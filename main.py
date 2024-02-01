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
import base64

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
      st.session_state.key = ""
      st.session_state.chordLevel = ""
      st.session_state.chordInfo = ""
      st.session_state.chordOption = []

os.environ["OPENAI_API_KEY"] = st.secrets.GPT3ApiKey.api_key
client = OpenAI()

IMAGE_FILE = './image.jpg'
DESCRIPTION_FILE = './description.txt'

MODE_GENERATE_PICTURE = 0
MODE_SUGGEST_CHORD = 1

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

def encode_image(image_path):
      with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

def main():
      #アプリ起動時の処理、二重にロードしたくない処理はここで行う
      if st.session_state.execInitProcess == False:
            if os.path.isfile(IMAGE_FILE):
                  os.remove(IMAGE_FILE)
            if os.path.isfile(DESCRIPTION_FILE):
                  os.remove(DESCRIPTION_FILE)
                  
            #初期化処理完了
            st.session_state.execInitProcess = True
      
      st.set_page_config(page_title = "写真で一曲")
      st.title("写真で一曲")
      mode = st.radio("モード選択", [":rainbow[画像生成]", ":rainbow[コード進行提案]"], captions = ["曲のイメージから画像を作るならこちら", "画像から曲のイメージに合うコード進行を提案してもらうならこちら"])
      
      if mode == ":rainbow[画像生成]":
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
            
            if st.sidebar.button("生成", key=1):
                  
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
                        description = open(DESCRIPTION_FILE, "w", encoding = "utf-8")
                        description.write(completion)
                        description.close()
                              
                        # 画像を取得
                        response = requests.get(responseUrl)
                        # 画像をファイルに保存
                        with open(IMAGE_FILE, 'wb') as f:
                              f.write(response.content)
                              
            if os.path.isfile(IMAGE_FILE) and os.path.isfile(DESCRIPTION_FILE):
                  image = Image.open(IMAGE_FILE)
                  description = open(DESCRIPTION_FILE, "r", encoding = "utf-8")
                  st.session_state.imageDescription = description.read()
                  st.image(image, caption="Description:" + st.session_state.imageDescription)
                  description.close()
      elif mode == ":rainbow[コード進行提案]":
            
            st.session_state.key = st.sidebar.selectbox("曲のキー", ["C", "C#/D♭", "D", "D#/E♭", "E", "F", "F#/G♭", "G", "G#/A♭", "A", "A#/B♭", "B"])
            st.session_state.chordLevel = st.sidebar.radio("コード進行レベル", ["ダイアトニックコード(初心者向け)", "ノンダイアトニックコード（中・上級者向け）"])
            if st.session_state.chordLevel == "ダイアトニックコード(初心者向け)":
                  st.session_state.chordInfo = st.sidebar.selectbox("コード進行レベル詳細", ["トライアドのみ", "セブンスコードあり"])
            else:
                  st.session_state.chordInfo = "セブンスを含めたダイアトニックコード"
                  st.session_state.chordOption= st.sidebar.multiselect("コード進行レベル詳細", ["sus", "aug", "dim", "add9", "テンションコード", "オルタードコード", "ブラックアダーコード", "部分転調", "オンコード", "ポリコード", "4度堆積コード", "クリシェ", "ペダルポイント"])
            
            uploaded_file = st.file_uploader("画像をアップロードしてください", type=["jpg"])
            if uploaded_file is not None:
                  image = Image.open(uploaded_file)
                  st.image(image)

            # 実行ボタン
            if st.button('コード進行作成'):
                  if uploaded_file is not None:
                        # 画像を一時的なファイルに保存
                        with open(IMAGE_FILE, "wb") as f:
                              f.write(uploaded_file.getbuffer())

                        base64_image = encode_image(IMAGE_FILE)
                        if st.session_state.chordLevel != "ダイアトニックコード(初心者向け)":
                              for option in st.session_state.chordOption:
                                    st.session_state.chordInfo = st.session_state.chordInfo + "、" + option
                        
                        prompt = f"この画像のイメージに合った曲を作りたいです。そのような曲のコード進行を、「{st.session_state.chordInfo}」の要素を必要に応じて取り入れて提案してください。ただし、コード進行のキーは{st.session_state.key}とし、出力は提案したコード進行のみとしてください。"
                        
                        # OpenAI APIを使用して画像の説明を取得
                        response = client.chat.completions.create(
                              model="gpt-4-vision-preview",
                              messages=[
                                    {
                                          "role": "user",
                                          "content": [
                                                {"type": "text", "text": prompt},
                                                {
                                                      "type": "image_url",
                                                      "image_url": {
                                                            "url": f"data:image/jpeg;base64,{base64_image}",
                                                            },
                                                },
                                          ],
                                    }
                              ],
                              max_tokens=1000,
                        )
                        # 結果の表示
                        st.success(response.choices[0].message.content, icon="🎹")
                        print(response.choices[0].message.content)

if __name__ == "__main__":
      main()