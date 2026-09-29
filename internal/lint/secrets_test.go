package lint

import (
	"strings"
	"testing"

	"github.com/frankbesch/memvet/internal/config"
)

func runSecrets(root string, cfg *config.Secrets) Result {
	return Run(root, &config.Config{Secrets: cfg})
}

func TestSecretsBuiltinPatterns(t *testing.T) {
	root := writeTree(t, map[string]string{
		"notes/card.md":  "gift card 4111 1111 1111 1111 pin 1234\n",
		"notes/aws.md":   "key AKIAIOSFODNN7EXAMPLE\n",
		"notes/gh.md":    "token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij\n",
		"notes/ant.md":   "sk-ant-api03-" + strings.Repeat("a", 40) + "\n",
		"notes/pem.md":   "-----BEGIN RSA PRIVATE KEY-----\n",
		"notes/clean.md": "order 1234-5678, D-102, phone 512-555-0100, not a card 1234567890123\n",
	})
	res := runSecrets(root, &config.Secrets{Globs: []string{"notes/*.md"}})
	wantCounts(t, res, 5, 0)
	for _, f := range res.Findings {
		if f.Path == "notes/clean.md" {
			t.Errorf("false positive: %s", f.Message)
		}
		if strings.Contains(f.Message, "4111 1111 1111 1111") || strings.Contains(f.Message, "AKIAIOSFODNN7EXAMPLE") {
			t.Errorf("a secret must never be echoed back: %s", f.Message)
		}
		if f.Code != "secrets/match" {
			t.Errorf("code %s", f.Code)
		}
	}
	if !hasFinding(res, "secrets", "notes/card.md", "card number") {
		t.Errorf("Luhn-valid card must be found:\n%s", dump(res))
	}
}

// Extra patterns are the repo's own; a stale zero-match glob is YELLOW.
func TestSecretsCustomPatternAndNoMatch(t *testing.T) {
	root := writeTree(t, map[string]string{"a.md": "internal id FB-SECRET-9\n"})
	res := runSecrets(root, &config.Secrets{Globs: []string{"*.md", "gone/*.md"}, Patterns: []string{`FB-SECRET-\d+`}})
	wantCounts(t, res, 1, 1)
	wantMessage(t, res, "custom pattern")
}

// Inside a git worktree the rule skips what git ignores: a file that can
// never be committed cannot reach history, which is all the rule guards.
// Untracked-but-not-ignored, tracked-despite-a-pattern, and no-git trees
// are scanned as before (D-191 item 9; incident 2026-09-18, a vendored
// doc under a gitignored .venv raised a false RED).
func TestSecretsHonorsGitignore(t *testing.T) {
	requireGit(t)
	const secret = "key AKIAIOSFODNN7EXAMPLE\n"
	cfg := &config.Secrets{Globs: []string{"**/*.md"}}

	t.Run("gitignored file is skipped", func(t *testing.T) {
		root := newRepo(t, map[string]string{".gitignore": "vendor/\n", "README.md": "clean\n"})
		writeFile(t, root, "vendor/doc.md", secret)
		writeFile(t, root, "notes/local.md", secret)
		writeFile(t, root, ".gitignore", "vendor/\nnotes/local.md\n")
		res := runSecrets(root, cfg)
		wantCounts(t, res, 0, 0)
		if res.FilesChecked != 1 {
			t.Errorf("FilesChecked = %d, want 1 (ignored files are not checked)", res.FilesChecked)
		}
	})

	t.Run("untracked but not ignored is a finding", func(t *testing.T) {
		root := newRepo(t, map[string]string{"README.md": "clean\n"})
		writeFile(t, root, "vendor/doc.md", secret)
		res := runSecrets(root, cfg)
		wantCounts(t, res, 1, 0)
		if !hasFinding(res, "secrets", "vendor/doc.md", "AWS access key") {
			t.Errorf("an untracked file is one git add from history:\n%s", dump(res))
		}
	})

	t.Run("tracked file matching an ignore pattern is still scanned", func(t *testing.T) {
		root := newRepo(t, map[string]string{"vendor/doc.md": secret})
		writeFile(t, root, ".gitignore", "vendor/\n")
		res := runSecrets(root, cfg)
		wantCounts(t, res, 1, 0)
		if !hasFinding(res, "secrets", "vendor/doc.md", "AWS access key") {
			t.Errorf("a tracked file is in history whatever .gitignore says:\n%s", dump(res))
		}
	})

	t.Run("no git means no skipping", func(t *testing.T) {
		root := writeTree(t, map[string]string{".gitignore": "vendor/\n", "vendor/doc.md": secret})
		res := runSecrets(root, cfg)
		wantCounts(t, res, 1, 0)
		if !hasFinding(res, "secrets", "vendor/doc.md", "AWS access key") {
			t.Errorf("without a worktree the rule must scan everything:\n%s", dump(res))
		}
	})
}

// luhnComplete appends the Luhn check digit to a digit prefix, so the
// false-positive cases below are built, never copied from a real file.
func luhnComplete(prefix string) string {
	for c := byte('0'); c <= '9'; c++ {
		if s := prefix + string(c); luhnValid(s) {
			return s
		}
	}
	panic("no check digit for " + prefix)
}

// The card detector fires on a payment card number, not on any digit run
// that happens to pass Luhn (one run in ten does). Incident 2026-09-29,
// D-230: 423 RED on well API numbers, coordinates, and float mantissas.
// Card numbers are the published test numbers from docs.stripe.com/testing.
func TestSecretsCardNumberShape(t *testing.T) {
	const visa = "4242424242424242"
	cases := []struct {
		name, line string
		want       bool
	}{
		// (a) part of a decimal number
		{"fraction", "lat 0." + visa, false},
		{"fraction-json", `"lon": -103.` + visa + `,`, false},
		{"fraction-13", "x 47." + luhnComplete("401234567890"), false},
		{"mantissa-exponent", "v 1." + visa + "e-05", false},
		{"integer-part", "v " + visa + ".25", false},
		// (b) JSON number and string tokens that are not cards
		{"json-number-14", `"api_no": ` + luhnComplete("4212345678901") + `,`, false},
		{"json-number-18", `"id": ` + luhnComplete("71234567890123456") + `}`, false},
		{"json-string-api", `"api_no": "` + hyphenate(luhnComplete("3310512345000"), 2, 3, 5, 2, 2) + `"`, false},
		// (c) length must fit the issuer: 14 digits is Diners only
		{"visa-prefix-14", "n " + luhnComplete("4000000000000"), false},
		{"visa-prefix-17", "n " + luhnComplete("4000000000000000"), false},
		{"amex-prefix-16", "n " + luhnComplete("378282246310005"), false},
		{"no-issuer-16", "n " + luhnComplete("100000000000000"), false},
		{"no-issuer-18-csv", "a," + luhnComplete("90000000000000000") + ",b", false},
		// (d) Luhn
		{"luhn-fail", "n 4242424242424241", false},

		// true positives
		{"visa", "card " + visa, true},
		{"visa-spaces", "card 4242 4242 4242 4242", true},
		{"visa-hyphens", "card 4242-4242-4242-4242", true},
		{"visa-sentence-end", "the card is " + visa + ".", true},
		{"visa-json-string", `"card": "` + visa + `"`, true},
		{"visa-json-number", `"card": ` + visa + `,`, true},
		{"visa-csv", "a," + visa + ",b", true},
		{"visa-debit", "4000056655665556", true},
		{"mastercard", "5555555555554444", true},
		{"mastercard-2-series", "2223003122003222", true},
		{"amex", "378282246310005", true},
		{"amex-grouped", "3782 822463 10005", true},
		{"discover", "6011111111111117", true},
		{"diners-16", "3056930009020004", true},
		{"diners-14", "36227206271667", true},
		{"jcb", "3566002020360505", true},
		{"unionpay", "6200000000000005", true},
		{"unionpay-19", "6205500000000000004", true},
	}
	files := map[string]string{}
	for _, c := range cases {
		files["n/"+c.name+".md"] = c.line + "\n"
	}
	res := runSecrets(writeTree(t, files), &config.Secrets{Globs: []string{"n/*.md"}})
	for _, c := range cases {
		if got := hasFinding(res, "secrets", "n/"+c.name+".md", "card number"); got != c.want {
			t.Errorf("%s: flagged = %v, want %v", c.name, got, c.want)
		}
	}
}

// hyphenate splits s into groups of the given sizes joined by hyphens.
func hyphenate(s string, sizes ...int) string {
	var parts []string
	for _, n := range sizes {
		parts = append(parts, s[:n])
		s = s[n:]
	}
	return strings.Join(parts, "-")
}
