import sys,os,json,re

# File paths
CHATBOT_TS = b'D:/resources-ai-chatbot-plugin-contribution/frontend/src/api/chatbot.ts'.decode()
CHATBOT_TSX = b'D:/resources-ai-chatbot-plugin-contribution/frontend/src/components/Chatbot.tsx'.decode()
MESSAGES_TSX = b'D:/resources-ai-chatbot-plugin-contribution/frontend/src/components/Messages.tsx'.decode()
INDEX_CSS = b'D:/resources-ai-chatbot-plugin-contribution/frontend/src/index.css'.decode()

# Read files
with open(CHATBOT_TS,'r',encoding='utf-8') as f: chatbot_src = f.read()
with open(CHATBOT_TSX,'r',encoding='utf-8') as f: chatbot_tsx = f.read()
with open(MESSAGES_TSX,'r',encoding='utf-8') as f: messages_tsx = f.read()
with open(INDEX_CSS,'r',encoding='utf-8') as f: index_css = f.read()

print('Files read')
