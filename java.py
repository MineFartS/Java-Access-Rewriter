import re

# Java Regex Patterns
# Matches method/field declarations that don't already have public/private/protected
JAVA_BLANK_MODIFIER = re.compile(
    r'(?P<indent>^\s*)(?!(?:public|private|protected|return|throw)\b)(?P<rest>(?:static\s+|final\s+|synchronized\s+|abstract\s+)*(?:[\w<>\[\]]+)\s+\w+\s*(?:;|=|\())', 
    re.MULTILINE
)

JAVA_PACKAGE_PRIVATE = re.compile(r'\b(protected|private)\b')

def java_replacer(match: re.Match):
    return f"{match.group('indent')}public {match.group('rest')}"

def rewrite(content):
    content = JAVA_PACKAGE_PRIVATE.sub('public', content)
    content = JAVA_BLANK_MODIFIER.sub(java_replacer, content)
    return content

