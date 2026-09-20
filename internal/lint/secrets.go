package lint

import (
	"fmt"
	"io/fs"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/frankbesch/memvet/internal/config"
)

const ruleSecrets = "secrets"

// secretPattern is one built-in detector. The finding names the kind and
// never echoes the matched text: a report that repeats a secret has just
// leaked it into the log.
type secretPattern struct {
	kind string
	re   *regexp.Regexp
	// luhn narrows digit runs to card numbers with a valid check digit, so
	// order numbers and phone numbers do not fire.
	luhn bool
}

var builtinSecrets = []secretPattern{
	{"AWS access key", regexp.MustCompile(`\b(?:AKIA|ASIA)[0-9A-Z]{16}\b`), false},
	{"GitHub token", regexp.MustCompile(`\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b`), false},
	{"Anthropic API key", regexp.MustCompile(`\bsk-ant-[A-Za-z0-9_-]{20,}`), false},
	{"OpenAI API key", regexp.MustCompile(`\bsk-(?:proj-)?[A-Za-z0-9]{32,}\b`), false},
	{"Slack token", regexp.MustCompile(`\bxox[abprs]-[A-Za-z0-9-]{10,}`), false},
	{"private key block", regexp.MustCompile(`-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY(?: BLOCK)?-----`), false},
	{"card number", regexp.MustCompile(`\b(?:\d[ -]?){12,18}\d\b`), true},
}

// checkSecrets scans the listed files for credential-shaped text. It is the
// working-tree half of a pre-commit tripwire: run it with --changed before
// committing and a card number or token cannot ride into history.
func checkSecrets(r *runner, cfg *config.Secrets) {
	patterns := builtinSecrets
	for _, p := range cfg.Patterns {
		patterns = append(patterns, secretPattern{kind: "custom pattern " + p, re: regexp.MustCompile(p)})
	}
	matched := make(map[string]bool, len(cfg.Globs))
	ignored := gitIgnored(r.root)
	r.walk(ruleSecrets, func(rel string, d fs.DirEntry) error {
		// A file git will never track cannot reach history, which is the
		// only thing this rule guards; a gitignored vendor tree full of
		// documented example card numbers is noise, not a tripwire.
		if ignored != nil && ignored(rel) {
			if d.IsDir() {
				return fs.SkipDir
			}
			return nil
		}
		if d.IsDir() || !d.Type().IsRegular() {
			return nil
		}
		any := false
		for _, g := range cfg.Globs {
			if globMatch(g, rel) {
				matched[g] = true
				any = true
			}
		}
		if !any {
			return nil
		}
		r.mark(rel)
		data, err := os.ReadFile(filepath.Join(r.root, filepath.FromSlash(rel)))
		if err != nil {
			r.cannotVerify(ruleSecrets, rel, err)
			return nil
		}
		for i, line := range strings.Split(string(data), "\n") {
			for _, p := range patterns {
				hit := false
				for _, m := range p.re.FindAllString(line, -1) {
					if !p.luhn || luhnValid(m) {
						hit = true
						break
					}
				}
				if hit {
					r.add(Finding{
						Rule: ruleSecrets, Code: "secrets/match", Severity: SeverityRed, Path: rel, Line: i + 1,
						Message: fmt.Sprintf("possible %s (value not shown)", p.kind),
					})
				}
			}
		}
		return nil
	})
	for _, g := range cfg.Globs {
		if !matched[g] {
			r.add(Finding{
				Rule: ruleSecrets, Code: "secrets/no-match", Severity: SeverityYellow, Path: g,
				Message: "globs entry matched no files",
				Detail:  "a stale glob is secret coverage that silently never runs",
			})
		}
	}
}

// luhnValid reports whether the digits in s pass the Luhn check.
func luhnValid(s string) bool {
	sum, alt, n := 0, false, 0
	for i := len(s) - 1; i >= 0; i-- {
		c := s[i]
		if c < '0' || c > '9' {
			continue
		}
		d := int(c - '0')
		if alt {
			d *= 2
			if d > 9 {
				d -= 9
			}
		}
		sum += d
		alt = !alt
		n++
	}
	return n >= 13 && sum%10 == 0
}

// gitIgnored returns a predicate over root-relative slash paths that reports
// whether git would never track them: untracked paths that an exclude rule
// matches, exactly as `git ls-files --others --ignored --exclude-standard
// --directory` lists them from root. A wholly ignored directory comes back
// as one "dir/" entry, so the predicate answers for its descendants too. A
// tracked file is never ignored whatever .gitignore says: it is in history
// already, so it is scanned. Git absent, root outside a worktree, or any
// git failure returns nil and the caller scans everything, as it always
// did: scanning more is the safe failure direction for a tripwire, and a
// silent narrowing is the one thing this rule must never do.
func gitIgnored(root string) func(rel string) bool {
	if _, err := exec.LookPath("git"); err != nil {
		return nil
	}
	out, err := gitOut(root, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z", "--", ".")
	if err != nil {
		return nil
	}
	files := map[string]bool{}
	var dirs []string
	for _, entry := range strings.Split(out, "\x00") {
		if entry == "" {
			continue
		}
		entry = filepath.ToSlash(entry)
		if strings.HasSuffix(entry, "/") {
			dirs = append(dirs, entry)
		} else {
			files[entry] = true
		}
	}
	return func(rel string) bool {
		if files[rel] {
			return true
		}
		for _, d := range dirs {
			if strings.HasPrefix(rel+"/", d) {
				return true
			}
		}
		return false
	}
}
