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
