# interpersonal-writing

[日本語](README.md) | English

An agent skill for writing messages to other people in Japanese, matched to your relationship with the reader and to what you need from them. It works with any agent that reads `SKILL.md`, such as Claude Code, Codex and Cursor.

- Media: email, chat (LINE, Slack and similar), contact forms, and flea-market transaction messages (Mercari)
- Readers: family, friends, coworkers, university teachers, people outside your organization, and customer-support or government desks
- Language: mainly Japanese. English is covered for email only (to professors, companies and customer support)

## What it does

1. **Chooses a politeness level (0–5) from the relationship.** Level 0 is a LINE message to your family; level 5 is a first email to a company or a professor. Each level fixes the sentence endings, the greeting, how to address the reader and how to close.
2. **Applies a template for the medium and the purpose.** Purposes: request, question, reporting a problem, complaint, thanks, apology, declining, follow-up, scheduling, submission and reply. For Mercari it covers questions before buying, asking for a discount, shipping, receiving and rating, problems with the item, and cancellation, following Mercari's official guide.
3. **Checks the draft with a script.** `scripts/check.py` flags double honorifics (二重敬語), humble forms used for the reader's actions, dates whose weekday is wrong, over-politeness, and missing signatures in email. In chat it also flags greeting-only messages, `@channel`, and signatures that chat does not need. In Mercari messages it flags phone numbers, SNS IDs, and payment outside Mercari.
4. **Remembers your own settings.** A profile file holds your signatures, the level you use with each person, how you address your family, and words you never use.

More honorifics do not make a message more polite. The government guideline on honorifics, *Keigo no Shishin* (Council for Cultural Affairs, 2007), says the same. The skill picks the simplest form within the chosen level.

## Install

```bash
npx skills add <owner>/interpersonal-writing
```

As a Claude Code plugin:

```text
/plugin marketplace add <owner>/interpersonal-writing
/plugin install interpersonal-writing@interpersonal-writing
```

Or copy `skills/interpersonal-writing/` into `~/.claude/skills/`.

## Profile

```bash
mkdir -p ~/.config/interpersonal-writing
cp skills/interpersonal-writing/profile.example.md ~/.config/interpersonal-writing/profile.md
```

Write your signatures, levels and forms of address in the copied file. It lives outside the skill folder so updates do not overwrite it. To keep it somewhere else, set `INTERPERSONAL_WRITING_PROFILE` to its path.

## Usage

Ask your agent in plain words:

```text
I want to email a company's recruiter to move my interview. I'm free on the afternoons of October 28 and 30.
```

```text
Fix the keigo in this email: (paste the text)
```

You can also run only the checker (Python 3.11 or later, no extra libraries):

```bash
python3 skills/interpersonal-writing/scripts/check.py mail.txt --level 4 --medium email --context job
```

Media are `email`, `chat`, `form` and `marketplace`. The output is in Japanese. Each line names the problem, a fix, and the source.

## Levels

| Level | Relationship | Example |
|---|---|---|
| 0 | Family | LINE to a parent |
| 1 | Friends | LINE to a friend |
| 2 | Peers on your side | Coworkers' group chat at a part-time job |
| 3 | Seniors on your side | The manager at your part-time job |
| 4 | Outside, ongoing | A company you are already talking to, a professor, a support desk |
| 5 | Outside, first contact | A company or a professor you have never contacted |

See [references/levels.md](skills/interpersonal-writing/references/levels.md) (Japanese).

## Sources

Every rule cites public bodies, universities, industry associations or the platform's own help pages. The core source is *Keigo no Shishin* (2007), cited down to the page and question number. Rules without such a source are marked as convention (慣用) or the author's judgment (私の判断). See [references/sources.md](skills/interpersonal-writing/references/sources.md).

## Tests

```bash
python3 -m unittest discover -s tests
```

The tests check that the script catches the errors it should and leaves alone forms the guideline accepts (とんでもございません, お伺いする, ご利用いただきまして and others).

## Prior work

These skills informed the structure. No text was copied. chezou/slop-nuki, robtar97/japanese-writing-skills, clawic/skills, yunyoumao/academic-email-jp-skill, ronantakizawa/japanese-email, davila7/claude-code-templates (all MIT).

## License

MIT
