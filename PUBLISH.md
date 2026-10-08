# Publishing to GitHub — `Maksmit0611/Sarrathi`

Your repository already exists: **<https://github.com/Maksmit0611/Sarrathi>**
It was created with an Apache-2.0 `LICENSE` and a placeholder README. This folder is already set up to
merge into it **without losing anything**.

---

## One command

```bash
cd sarathi-labs
bash push_to_sarrathi.sh
```

That script:

1. commits anything outstanding
2. **fetches your GitHub repo and merges the two histories** — so your `LICENSE` and commit history stay
3. keeps the Apache-2.0 `LICENSE` you chose on GitHub
4. pushes everything

It is safe to run repeatedly.

### When git asks for a password

| Field | Enter |
|---|---|
| Username | `Maksmit0611` |
| Password | a **Personal Access Token**, *not* your account password |

Create a token: <https://github.com/settings/tokens> → **Fine-grained token** →
Repository access: `Sarrathi` → Permissions: **Contents = Read and write**.

Prefer SSH? Then:

```bash
git remote set-url origin git@github.com:Maksmit0611/Sarrathi.git
git push -u origin main
```

---

## Alternative: no terminal at all

1. Download `sarathi-labs.zip` from the workspace and unzip it
2. Open <https://github.com/Maksmit0611/Sarrathi>
3. **Add file → Upload files** → drag everything in → Commit

This works, but ruins your history (one giant commit) and won't preserve `.github/workflows/ci.yml`
unless the folders are dragged in too. The script is better.

> **Note:** because `LICENSE` and `README.md` already exist on GitHub, a *force push* would delete
> them. `push_to_sarrathi.sh` merges instead, which is why it's the recommended path.

---

## Before you push — 4 checks

- [ ] **No secrets.** `.env` is git-ignored and `.env.example` has empty values. The push script also greps for key patterns and aborts if it finds one.
- [ ] **Spelling of the lab name.** Your repo is `Sarrathi` (double-r) and one of your commits fixed `Sarrathi` → `Sarathii`. The canonical Sanskrit is **Sarathi** (सारथि) — one r, one i. Renaming is free and GitHub redirects old URLs, so this is the cheapest moment to fix it. → *Settings → Repository name*. (The product name **Arthabodh** is unaffected either way.)
- [ ] **Licence.** You chose **Apache-2.0** on GitHub; the repo now uses it, replacing the earlier MIT text. Fine for code — but note `data/README.md`: the **culture data is research-use only** and the case-file compilation is **CC BY 4.0**. Those terms are separate from the code licence and worth reading before any commercial use.
- [ ] **git identity.** Set it so commits are attributed to you:
      `git config user.name "Your Name" && git config user.email "you@example.com"`

---

## After the push

1. **Check the Actions tab.** CI runs on every push: it enforces the stdlib-only promise, compiles everything, validates the corpus schema, runs **63 regression tests**, and boots the server on Python 3.10 and 3.12.
2. **Paste the description and topics** from `docs/GITHUB_LISTING.md` into the About panel (the description is already set; the topics are empty).
3. **Upload a social preview image** — Settings → Social preview. A screenshot of a real report roughly doubles click-through.
4. **Pin the repo** on your profile.

## Every time after that

```bash
git add -A && git commit -m "Add 5 case files: Indonesian food delivery" && git push
```

CI re-validates the corpus on every push — the cheapest way to keep the data honest.
