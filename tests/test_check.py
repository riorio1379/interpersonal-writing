"""check.py の試験。拾うべきものを拾い、指針が問題ないとするものを拾わないことを確かめる。

    python3 -m unittest discover -s tests
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "interpersonal-writing"
CHECK = SKILL / "scripts" / "check.py"
EXAMPLE_PROFILE = SKILL / "profile.example.md"


def run(text: str, level: int = 4, medium: str = "chat", *extra: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(CHECK), "-", "--level", str(level), "--medium", medium,
         "--profile", str(EXAMPLE_PROFILE), "--today", "2026-10-20", "--json", *extra],
        input=text, capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(proc.stdout)


def words(result: dict, category: str) -> list[str]:
    return [f["text"] for f in result["findings"] if f["category"] == category]


class FindsErrors(unittest.TestCase):
    """敬語の指針などが誤り・不適切とするものを拾う。"""

    cases = {
        "先生がおっしゃられた通りです。": "おっしゃられ",
        "資料をご覧になられましたか。": "ご覧になられ",
        "先生がお読みになられた本です。": "お読みになられ",
        "お手数ですが、ご確認してください。": "ご確認してください",
        "ご連絡していただけますか。": "ご連絡していただ",
        "詳細は受付で伺ってください。": "伺ってください",
        "説明会にご出席されますか。": "ご出席されま",
        "会員の方はご利用できます。": "ご利用でき",
        "私のお考えをお伝えします。": "私のお考え",
        "山田先生御中": "先生御中",
        "明日は休まさせていただきます。": "休まさせて",
        "部長が参られました。": "参られ",
    }

    def test_each(self):
        for text, expected in self.cases.items():
            with self.subTest(text=text):
                found = words(run(text), "誤り")
                self.assertTrue(any(expected in w for w in found), f"{expected} を拾っていない: {found}")


class LeavesAcceptedForms(unittest.TestCase):
    """指針が問題ない・定着しているとするものは拾わない。"""

    texts = [
        "明日、研究室にお伺いいたします。",
        "とんでもございません。",
        "ご利用いただきまして、ありがとうございます。",
        "ご利用くださいまして、ありがとうございます。",
        "どうぞお召し上がりになってください。",
        "先生がお見えになりました。",
        "ご確認ください。",
        "お待ちしております。",
        "改めてご連絡いたします。",
        "資料を拝見しました。",
        "そのように申し伝えます。",
        "当日はご持参ください。",
        "上司の方にお願いしていただけますか。",
        "2026年10月20日（火）は空いています。",
    ]

    def test_no_errors(self):
        for text in self.texts:
            with self.subTest(text=text):
                self.assertEqual(words(run(text), "誤り"), [])


class Weekdays(unittest.TestCase):
    def test_wrong_weekday(self):
        self.assertIn("10月21日（火）", words(run("10月21日（火）に伺います。"), "誤り"))

    def test_slash_format(self):
        self.assertIn("11/3(月)", words(run("11/3(月)はいかがでしょうか。"), "誤り"))

    def test_correct_weekday(self):
        self.assertEqual(words(run("10月21日（水）に伺います。"), "誤り"), [])


class Cautions(unittest.TestCase):
    def test_gosha_in_email(self):
        self.assertIn("御社", words(run("御社を志望しております。", 4, "email"), "注意"))

    def test_gosha_in_chat_is_ignored(self):
        self.assertNotIn("御社", words(run("御社を志望しております。", 4, "chat"), "注意"))

    def test_repeated_saseteitadaku(self):
        text = "説明させていただきます。\n確認させていただきました。"
        self.assertIn("させていただく", words(run(text), "注意"))

    def test_too_formal_for_family(self):
        self.assertIn("いたします", words(run("明日帰省いたします", 0, "chat"), "注意"))

    def test_style_mix(self):
        text = "資料をお送りします。\n来週が締切だ。"
        self.assertTrue(run(text)["counts"]["注意"] >= 1)


class EmailShape(unittest.TestCase):
    good = """株式会社サンプル
人事部 佐藤様

お世話になっております。
○○大学 経済学部 3年の山田花子です。

面接日程についてご相談したく、ご連絡いたしました。

よろしくお願いいたします。

山田 花子（やまだ はなこ）
電話：090-0000-0000
メール：hanako@example.com
"""

    def test_good_email(self):
        result = run(self.good, 4, "email", "--subject", "面接日程のご相談（○○大学 山田花子）")
        self.assertEqual(result["counts"]["型"], 0, result["findings"])
        self.assertEqual(result["counts"]["誤り"], 0, result["findings"])

    def test_missing_address(self):
        text = self.good.replace("株式会社サンプル\n人事部 佐藤様\n\n", "")
        self.assertGreaterEqual(run(text, 4, "email")["counts"]["型"], 1)

    def test_missing_signature_line(self):
        text = self.good.replace("電話：090-0000-0000\n", "")
        self.assertIn("電話：", words(run(text, 4, "email"), "型"))

    def test_job_signature_needs_university(self):
        self.assertIn("大学", words(run(self.good, 4, "email", "--context", "job"), "型"))

    def test_only_between_separators(self):
        text = "見出し：御社あて\n──────\n" + self.good + "──────\nメモ：御社\n"
        self.assertEqual(run(text, 4, "email")["counts"]["注意"], 0)


class Marketplace(unittest.TestCase):
    def test_phone_number(self):
        self.assertTrue(words(run("090-1234-5678 に連絡ください", 4, "marketplace"), "誤り"))


class ProfileRules(unittest.TestCase):
    def test_forbidden_first_person(self):
        self.assertIn("私は", words(run("私は明日帰るね", 0, "chat"), "誤り"))


if __name__ == "__main__":
    unittest.main()
