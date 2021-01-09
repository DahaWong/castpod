def generate_tag(text):
    return '#' + re.sub(r'\W', '', text)