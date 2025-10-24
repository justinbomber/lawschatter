import re
result = "123 456 789"
result = re.sub(r'\s+', '', result).strip()
print(result)