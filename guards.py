import re
import unicodedata


class InputError(ValueError):
    """A practice detail needs to be corrected before any API request."""


def validate_input(job_title: str, years: int) -> tuple[str, int]:
    if not isinstance(job_title, str):
        raise InputError("Enter a job title such as Python Developer.")
    role = job_title.strip()
    if not 2 <= len(role) <= 120:
        raise InputError("Enter a job title between 2 and 120 characters.")
    if not any(character.isalpha() for character in role):
        raise InputError("Include the name of the role, such as Python Developer.")
    if not re.fullmatch(r"[\w .,+/#&()'’\-]+", role, flags=re.UNICODE):
        raise InputError("Enter only a job title on one line, without links or instructions.")
    reject_instructions(role)
    if re.search(r"https?://|www\.", role, flags=re.IGNORECASE):
        raise InputError("Enter a job title without links.")
    normalized_role = unicodedata.normalize("NFKC", role).casefold()
    if re.search(
        r"\b(?:escort[\W_]*services?|(?:adult|sexual)[\W_]+escorts?|"
        r"hit[\W_]*(?:man|men|woman|women)|contract[\W_]*killers?|assassins?)\b|"
        r"\u6bba\u3057\u5c4b|\u30a8\u30b9\u30b3\u30fc\u30c8\u30b5\u30fc\u30d3\u30b9",
        normalized_role,
    ):
        raise InputError("This role is outside the scope of this practice app. Choose another job title.")
    if type(years) is not int or years < 0:
        raise InputError("Enter a whole number of years, 0 or greater.")
    return role, years


def reject_instructions(text: str) -> None:
    """Catch explicit instruction attempts; semantic checking follows before generation."""
    if re.search(
        r"\bignore\s+(?:all\s+|the\s+|previous\s+|above\s+)*(?:instructions?|prompts?|rules?)\b|"
        r"\b(?:reveal|show|print)\s+(?:the\s+|your\s+)?(?:system\s+prompt|api\s+key|hidden\s+instructions?|secrets?)\b",
        text,
        flags=re.IGNORECASE,
    ):
        raise InputError("Use interview practice input without instructions to change the AI's task or reveal secrets.")


def validate_answer(answer: str) -> str:
    if not isinstance(answer, str) or not 1 <= len(answer.strip()) <= 4000:
        raise InputError("Write an answer of up to 4,000 characters before requesting feedback.")
    reject_instructions(answer)
    return answer.strip()
