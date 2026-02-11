import re
from nltk.corpus import stopwords

def preprocess(text):
    text = re.sub(r'[^a-zA-Z ]', ' ', text)
    text = text.lower()
    words = text.split()
    words = [w for w in words if w not in stopwords.words('english')]
    return " ".join(words)
