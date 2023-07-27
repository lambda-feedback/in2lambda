import re
import json
import os
from datetime import datetime
import shutil

class Question:

    

    def __init__(self):
        self.title = 'Unnamed Question'
        self.text = ''
        self.part = []
        self.st = []
        self.fa = []
        self.ws = []
        return

    def set_title(self, q_title):
        self.title = q_title

    def set_text(self, q_text):
        self.text = q_text

    def append_part(self, part = '', st = '', fa = '', ws = ''):
        self.part.append(part)
        self.st.append(st)
        self.fa.append(fa)
        self.ws.append(ws)

    def display(self):
        print("**Title   **: ", end='')
        print(self.title)
        print("**Question**: ", end='')
        print(self.text)
        print("**Part    **: ", end='')
        print(self.part)
        print("**st      **: ", end='')
        print(self.st)
        print("**fa      **: ", end='')
        print(self.fa)
        print("**ws      **: ", end='')
        print(self.ws)
        print()
        
 

def openMD(fileName):
    md_file = open(fileName, 'r') #open file    
    lines = md_file.read()

    md_file.close()
    return lines

def splitMD(lines):

    output = ''

    #Clean input
    for line in lines.split('\n'): 
        if '#' in line: #Remove leading spaces if string contains a '#'
            line = line.lstrip()
                 
        output += line + '\n'

    lines = output

    content = []


    #If see a '#' get all until next '#' or eof
    questions = [line + '\n' for line in lines.split('\n# ')[1:]]
    for q in questions:
        newQ = Question()
        #split into title, text and parts
        q = q.split('\n', 1)
        qTitle = q[0]
        q = q[1]
        q = q.split('#', 1)
        qText = q[0]
        qParts = '#' + q[1]

        newQ.set_title(qTitle)
        newQ.set_text(qText)

        qParts = qParts.split('## \part')
        for p in qParts:
            if not p == '':
                p = p + '#'
                pText = p.split('###', 1)[0][1:]

                pSt = ''
                pFa = ''
                pWs = ''
                
                if '### \\st' in p:
                    pSt = p.split('### \\st', 1)[1].split('#', 1)[0][1:]
                if '### \\fa' in p:
                    pFa = p.split('### \\fa', 1)[1].split('#', 1)[0][1:]
                if '### \\ws' in p:
                    pWs = p.split('### \\ws', 1)[1].split('#', 1)[0][1:]
                    

                newQ.append_part(part = pText, st = pSt, fa = pFa, ws = pWs)

        content.append(newQ)
    
    return content



def JSONify(content):
    date = None
    output = []
    for q in content:
        JSON_str = """{
  "type": "DRAFT",
  "id": "NA",
  "versionId": "NA",
  "hasBeenPublished": false,
  "createdAt": "",
  "updatedAt": "",
  "title": \"""" + repr(q.title)[1:-1] + """\",
  "number": 0,
  "masterContent": {
    "blocks": [
      {
        "__typename": "TextContentBlock",
        "id": "N/A",
        "data": \"""" + repr(q.text)[1:-1] + """\",
        "type": "MILKDOWN"
      }
    ]
  },
    "parts": ["""
        for i in range(0, len(q.part)):
            JSON_str += """
    {
      "id": "NA",
      "universalPartId": "",
      "content": {
        "blocks": [
          {
            "__typename": "TextContentBlock",
            "id": "N/A",
            "data": \"""" + repr(q.part[i])[1:-1] + """\",
            "type": "MILKDOWN"
          }
        ]
      },
      "workedSolution": [
        {
          "id": "NA",
          "content": {
            "blocks": [
              {
                "__typename": "TextContentBlock",
                "id": "N/A",
                "data": \"""" + repr(q.ws[i])[1:-1] + """\",
                "type": "MILKDOWN"
              }
            ]
          }
        }
      ],
      "answerContent": {
        "blocks": [
          {
            "__typename": "TextContentBlock",
            "id": "N/A",
            "data": \"""" + repr(q.fa[i])[1:-1] + """\",
            "type": "MILKDOWN"
          }
        ]
      },

      "tutorial": ["""
            st = q.st[i].split("***")
            for j in range(0, len(st)):
                JSON_str += """
        {
          "id": "NA",
          "content": {
            "blocks": [
              {
                "__typename": "TextContentBlock",
                "id": "N/A",
                "data": \"""" + repr(st[j])[1:-1] + """\",
                "type": "MILKDOWN"
              }
            ]
          }
        },"""
            JSON_str = JSON_str[:-1] + """
      ],

      "responseAreas": []
    },"""
        JSON_str = JSON_str[:-1] + """
  ]
}""" #remove the final comma and add the closing perenthesis
        JSON_str = JSON_str.replace('media\\\\', '')
        JSON_str = JSON_str.replace('$$', '\\n$$\\n')
        output.append(JSON_str)
    return output



def main():

    folderPath = input("Folder path: ")

    if "\"" in folderPath:
        folderPath = folderPath[1:-1]
    

    lines = openMD(folderPath + r'\template.md')    

    output = splitMD(lines)

    JSON_strs = JSONify(output)
    
    count = 1
    for q in JSON_strs:
        
        #create folder for question
        newFolder = os.path.join(folderPath, str(count))
        if os.path.exists(newFolder):
            shutil.rmtree(newFolder)
        os.makedirs(newFolder)
        
        #save json file
        f = open(f"{newFolder}/{'data'}.json", 'w')
        for l in q:
            f.write(l)
        f.close()
           
        #copy media folder into folder for question, only if media file is there
        if os.path.existsos.path.join(folderPath, r'media'):
            shutil.copytree(os.path.join(folderPath, r'media'), os.path.join(newFolder, r'media'))
        #zip folder        
        shutil.make_archive(newFolder, 'zip', newFolder)
        count += 1



if __name__ == '__main__':
    main()
