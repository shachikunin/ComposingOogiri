import streamlit as st
import base64
import time
import os
import re
import numpy as np
import urllib.request,urllib.parse
import requests
import datetime
from openai import OpenAI
from PIL import Image
import io
import random

if "chatHistory" not in st.session_state:
      st.session_state.execInitProcess = False
      st.session_state.who = ""
      st.session_state.what = ""
      st.session_state.when = ""
      st.session_state.where = ""
      st.session_state.why = ""
      st.session_state.how = ""
      st.session_state.info = ""
      st.session_state.imageDescription = ""
      st.session_state.disableRandomInputWho = False
      st.session_state.disableRandomInputWhat = False
      st.session_state.disableRandomInputWhen = False
      st.session_state.disableRandomInputWhere = False
      st.session_state.disableRandomInputWhy = False
      st.session_state.disableRandomInputHow = False
      st.session_state.disableRandomInputInfo = False

os.environ["OPENAI_API_KEY"] = st.secrets.GPT3ApiKey.api_key
client = OpenAI()

def generate_random_word(keyword):
      num = random.randrange(3) + 1
      completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
            {"role": "user", "content": "あなたはランダムな単語を" + str(num) + "個生成するAIです。ただし、出力は最大文字数20文字以内とし、複数あればカンマで区切り、日本語で出力してください。また、形容詞があっても名詞であることも守ってください。"},
            {"role": "user", "content": keyword + "に関するランダムな修飾語、または形容詞や副詞などが付いた単語を生成してください。生成される内容は、固有名詞が含まれてもよいです。"}
            ],
            temperature=0.7,
            max_tokens = 30
      )

      return completion.choices[0].message.content

def fill_random_word():
      if st.session_state.disableRandomInputWho == False:
            st.session_state["textBoxWho"] = generate_random_word("人物や動物などターゲット(Who)")
      if st.session_state.disableRandomInputWhat == False:
            st.session_state["textBoxWhat"] = generate_random_word("目的となる対象の行動や動作(What)")
      if st.session_state.disableRandomInputWhen == False:
            st.session_state["textBoxWhen"] = generate_random_word("季節や時間帯(When)")
      if st.session_state.disableRandomInputWhere == False:
            st.session_state["textBoxWhere"] = generate_random_word("国や地名など場所(Where)")
      if st.session_state.disableRandomInputWhy == False:
            st.session_state["textBoxWhy"] = generate_random_word("理由や原因、背景(Why)")
      if st.session_state.disableRandomInputHow == False:
            st.session_state["textBoxHow"] = generate_random_word("目的を達成するための手段(How)")
      if st.session_state.disableRandomInputHow == False:
            st.session_state["textBoxInfo"] = generate_random_word("楽曲のジャンル、絵の画風")

def make_image(text):
      print(text)
      start = time.time()  # 現在時刻（処理開始前）を取得
      response = client.images.generate(
            model="dall-e-3",
            prompt=text,
            size="1024x1024",
            quality="standard",
            n=1,
            )
      
      end = time.time()  # 現在時刻（処理完了後）を取得

      time_diff = end - start  # 処理完了後の時刻から処理開始前の時刻を減算する
      st.write("Time:" + str(round(time_diff, 2)) + "[s]")  # 処理にかかった時間データを使用
      
      return response.data[0].revised_prompt, response.data[0].url

def main():
      #アプリ起動時の処理、二重にロードしたくない処理はここで行う
      if st.session_state.execInitProcess == False:
            
            #初期化処理完了
            st.session_state.execInitProcess = True
      
      st.set_page_config(page_title = "写真で一曲")
      st.title("写真で一曲")
      
      st.sidebar.title("曲のイメージ")
      st.session_state.who = st.sidebar.text_input("Who(例：白熊)", key = "textBoxWho")
      st.session_state.disableRandomInputWho = st.sidebar.checkbox("Whoをランダム入力しない")
      st.session_state.what = st.sidebar.text_input("What(例：俯きながらヘッドホンで音楽を聴いている)", key = "textBoxWhat")
      st.session_state.disableRandomInputWhat = st.sidebar.checkbox("Whatをランダム入力しない")
      st.session_state.when = st.sidebar.text_input("When(例：満点の星空が見える真夜中)", key = "textBoxWhen")
      st.session_state.disableRandomInputWhen = st.sidebar.checkbox("Whenをランダム入力しない")
      st.session_state.where = st.sidebar.text_input("Where(例：小さな明かりが灯る部屋の中)", key = "textBoxWhere")
      st.session_state.disableRandomInputWhere = st.sidebar.checkbox("Whereをランダム入力しない")
      st.session_state.why = st.sidebar.text_input("Why(例：好きな曲を聴きながら眠るため)", key = "textBoxWhy")
      st.session_state.disableRandomInputWhy = st.sidebar.checkbox("Whyをランダム入力しない")
      st.session_state.how = st.sidebar.text_input("How(例：椅子に座って頬杖をついて)", key = "textBoxHow")
      st.session_state.disableRandomInputHow = st.sidebar.checkbox("Howをランダム入力しない")
      st.session_state.info = st.sidebar.text_input("Supplementary information(例：画風は水彩画の淡いタッチとする。曲のジャンルはlofi系)", key = "textBoxInfo")
      st.session_state.disableRandomInputHow = st.sidebar.checkbox("Supplementary informationをランダム入力しない")
      st.sidebar.button("ランダム入力", key=0, on_click=fill_random_word)
      
      if st.button("生成", key=1):
            
            if st.session_state.who == "" or st.session_state.what == "" or st.session_state.when == "" or st.session_state.where == "" or st.session_state.why == "" or st.session_state.how == "" or st.session_state.info == "":
                  st.error("全ての情報を入力してください。")
            else:
                  with st.spinner('画像生成中...'):
                        message = f"""5W1Hと補足情報の形式で、以下にそれぞれの情報を提供しますので、それらを踏まえて画像を生成してください。ただし、プロンプトは英語としてください。：
            * Who: {st.session_state.who}
            * What: {st.session_state.what}
            * When: {st.session_state.when}
            * Where: {st.session_state.where}
            * Why: {st.session_state.why}
            * How: {st.session_state.how}
            * Supplementary information: {st.session_state.info}"""
                        completion, responseUrl = make_image(message)
                  
                  st.session_state.imageDescription = completion
                  description = open("description.txt", "w", encoding = "utf-8")
                  description.write(completion)
                  description.close()
                        
                  # 画像を取得
                  response = requests.get(responseUrl)
                  # 画像をファイルに保存
                  with open('image.jpg', 'wb') as f:
                        f.write(response.content)
                        
      if os.path.isfile('./image.jpg') and os.path.isfile('./description.txt'):
            image = Image.open('image.jpg')
            description = open("description.txt", "r", encoding = "utf-8")
            st.session_state.imageDescription = description.read()
            st.image(image, caption="Description:" + st.session_state.imageDescription)
            description.close()
      
            

if __name__ == "__main__":
      main()