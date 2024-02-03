import streamlit as st
import base64
import time
import os
import shutil
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
from mido import Message, MidiFile, MidiTrack, bpm2tempo, MetaMessage
from midi2audio import FluidSynth

if "execInitProcess" not in st.session_state:
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
      st.session_state.chordProgression = ""

os.environ["OPENAI_API_KEY"] = st.secrets.GPT3ApiKey.api_key
client = OpenAI()

IMAGE_FILE = './image.jpg'
IMAGE_TMP_FILE = './image_tmp.jpg'
DESCRIPTION_FILE = './description.txt'
MIDI_FILE = './chord.mid'
CHORD_AUDIO = './chord.wav'

MODE_GENERATE_PICTURE = 0
MODE_SUGGEST_CHORD = 1

# 基本のMIDIノート番号 (C4の場合は60)
note_map = {
      "C": 60, "C#": 61, "Db": 61, "D": 62, "D#": 63, "Eb": 63, 
      "E": 64, "F": 65, "F#": 66, "Gb": 66, "G": 67, "G#": 68, "Ab": 68, 
      "A": 69, "A#": 70, "Bb": 70, "B": 71
}

# コードタイプに応じたオフセットのパターン
chord_types = {
      "": [0, 4, 7],  # メジャーコード
      "m": [0, 3, 7],  # マイナーコード
      "7": [0, 4, 7, 10],  # ドミナントセブンスコード
      "maj7": [0, 4, 7, 11],  # メジャーセブンスコード
      "m7": [0, 3, 7, 10],  # マイナーセブンスコード
      "sus4": [0, 5, 7],  # サスフォー
      "7sus4": [0, 5, 7],  # サスフォー
      "sus2": [0, 2, 7],  # サスツー
      "add9": [0, 4, 7, 14],  # アドナイン
      "aug": [0, 4, 8],  # オーギュメント
      "aug7": [0, 4, 8, 10],  # オーギュメントセブンス
      "dim": [0, 3, 6],  # ディミニッシュ
      "dim7": [0, 3, 6, 9],  # ディミニッシュセブンス
      "m7b5": [0, 3, 6, 10],  # マイナーセブンスフラットファイブ
      "6": [0, 4, 7, 9],  # メジャーシックス
      "m6": [0, 3, 7, 9],  # マイナーシックス
      "m9": [0, 3, 7, 10, 14],  # マイナー9コード
      "9": [0, 4, 7, 10, 14],  # 9コード
      "m11": [0, 3, 7, 10, 14, 17],  # マイナー11コード
      "11": [0, 4, 7, 10, 14, 17],  # 11コード
      "13": [0, 4, 7, 10, 14, 21],  # 13コード
      "7b13": [0, 4, 7, 10, 20],  # 7b13コード
}

def get_chord_notes(chord):
      notes = []  # 最終的なノートリスト
      max_pitch = 75  # 最大の音高
      bass_offset = 24  # ベースノートをコードノートより24MIDIノート（2オクターブ）下げる
      #print("input:" + chord)

      # オンコードまたは通常のコードの解析
      if '/' in chord:
            chord_part, bass_part = chord.split('/')
      else:
            chord_part = chord
            bass_part = chord_part  # ルートノートをベースとして使用

      # コード部分のノートを生成
      chord_notes = generate_notes(chord_part)
      # ベースノートの生成（ルートノートまたは指定されたベース）
      bass_note = note_map.get(bass_part[0], 60)  # ベースノートが見つからない場合のデフォルト値
      if len(bass_part) > 1 and bass_part[1] in ['#', 'b']:  # シャープやフラットの考慮
            modifier = 1 if bass_part[1] == '#' else -1
            bass_note += modifier

      # ベースノートを2オクターブ下げてリストの最初に追加
      bass_note -= bass_offset
      notes = [bass_note] + chord_notes

      return notes

def generate_notes(chord):
      # コードタイプを特定し、対応するノートを生成
      for root_note in sorted(note_map.keys(), key=lambda x: -len(x)):  # 最長一致でキーを検出
            if chord.startswith(root_note):
                  chord_type = chord[len(root_note):]
                  base_note = note_map[root_note]
                  offsets = chord_types.get(chord_type, [])
                  notes = [(base_note + offset) % 12 + base_note - base_note % 12 for offset in offsets]
                  return notes
      return []  # コードがマッピングに存在しない場合は空リストを返す

def create_midi_from_progression(progression, output_path, bpm=120, note_length='half', velocity=64):
      # 有効な文字セットを定義(対応コードを増やしたら、ここも増やす)
      valid_chars = "ABCDEFGabcdefg#♭bmajmin7sus2sus4add9dimaug/-°+"
      valid_strings = ['m', 'maj', 'min', 'dim', 'aug', '7', 'm7', 'maj7', 'dim7', 'm9', '9', 'm11', '11', '13', '7b13', '6', 'm6', 'sus2', 'sus4', 'add9', 'b5', '#5', 'b9', '#9', 'b11', '#11', 'b13', '#13', "/", "-"]
      result = True
      
      mid = MidiFile()
      track = MidiTrack()
      mid.tracks.append(track)

      # BPMを設定
      track.append(MetaMessage('set_tempo', tempo=bpm2tempo(bpm), time=0))
      
      # 音の長さを設定（デフォルトは四分音符）
      length_map = {
            'whole': 4,
            'half': 2,
            'quarter': 1,
            'eighth': 0.5,
            'sixteenth': 0.25,
      }
      note_duration = int(480 * length_map.get(note_length, 1))  # MidiファイルのデフォルトTPQを使用
      
      # 改行コードを-、♭をbに、「 」を-に置き換え、全角文字を半角文字にする
      progression = progression.replace('\n', '-')
      progression = progression.replace('♭', 'b')
      progression = progression.replace('(', '')
      progression = progression.replace(')', '')
      progression = progression.replace(' ','-')
      progression = progression.translate(str.maketrans('ＡＢＣＤＥＦＧａｂｃｄｅｆｇ', 'ABCDEFGabcdefg'))
      chords = progression.split('-')
      # 空文字の要素を削除して、コードのみを含むリストを生成
      chords = [chord for chord in chords if chord]
      
      # コード進行文字列の検証
      for chord in chords:
            # 有効な文字列のチェック
            if not any(valid_string in chord for valid_string in valid_strings):
                  # 有効な文字のみで構成されているかチェック
                  if not all(char in valid_chars for char in chord):
                        return False  # 有効でない文字が含まれている
      
      for chord in chords:
            notes = get_chord_notes(chord)
            notes.sort()
            #print(notes)
            # ノートオン
            for note in notes:
                  track.append(Message('note_on', note=note, velocity=velocity, time=0))
            # ノートオフ
            for note in notes:
                  #int(note_duration*4/len(notes)は、ノートの数によって音の長さが変わるのを防いでいる
                  track.append(Message('note_off', note=note, velocity=velocity, time=int(note_duration*4/len(notes))))
      
      # MIDIファイルの保存
      mid.save(output_path)
      
      return result

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
      #print(text)
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
            # streamlitの環境がわからないので、一旦Windows以外にする
            if os.name != "nt":
		    os.mkdir("/home/appuser/.fluidsynth")
	            shutil.copy("/usr/share/sounds/sf2/FluidR3_GM.sf2", "/home/appuser/.fluidsynth/default_sound_font.sf2")
            if os.path.isfile(IMAGE_FILE):
                  os.remove(IMAGE_FILE)
            if os.path.isfile(DESCRIPTION_FILE):
                  os.remove(DESCRIPTION_FILE)
            if os.path.isfile(MIDI_FILE):
                  os.remove(MIDI_FILE)
            # コード進行確認用wavファイルは削除
            files = os.listdir()
            for file in files:
                  if file.endswith(".wav"):
                        os.remove(file)
                  
            #初期化処理完了
            st.session_state.execInitProcess = True
      
      st.set_page_config(page_title = "写真で一曲")
      st.title("写真で一曲")
      mode = st.radio("モード選択", [":rainbow[画像生成]", ":rainbow[コード進行提案]"], captions = ["曲のイメージから画像を作るならこちら", "画像から曲のイメージに合うコード進行を提案してもらうならこちら"])
      
      if mode == ":rainbow[画像生成]":
            st.session_state.chordProgression = ""
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
                  st.session_state.chordOption= st.sidebar.multiselect("コード進行レベル詳細", ["sus4", "aug", "dim", "add9", "テンションコード", "オルタードコード", "ブラックアダーコード", "部分転調", "オンコード", "ポリコード", "クリシェ", "ペダルポイント"])
            chordText = st.sidebar.text_input('コード進行作成でできたコード進行を入力すると、どんな音になるか確認できます')
            selectBPM = st.sidebar.slider('コード進行のBPM', 60, 200, 120)
            selectVelocity = st.sidebar.slider('ベロシティ（音量）', 0, 127, 100)
            
            if st.sidebar.button("生成", key=1, disabled = chordText == ""):
                  result = create_midi_from_progression(chordText, MIDI_FILE, bpm=selectBPM, note_length='eighth', velocity=selectVelocity)
                  if result:
                        #MIDI->audio
                        fs = FluidSynth()
                        fs.midi_to_audio(MIDI_FILE, CHORD_AUDIO)
                  else:
                        st.sidebar.error("使用できない文字があります。コードを表す文字かどうかご確認ください。")
                  
            if os.path.isfile(CHORD_AUDIO):
                  audio_file = open(CHORD_AUDIO, 'rb')
                  audio_bytes = audio_file.read()
                  st.sidebar.audio(audio_bytes, format='audio/wav')
            
            if os.path.isfile(MIDI_FILE):
                  with open(MIDI_FILE, "rb") as file:
                              st.sidebar.download_button(
                                    label="MIDIファイルをダウンロード",
                                    data=file,
                                    file_name=chordText + ".mid"
                              )
            
            imageList = []
            loadImage = "NoImage"
            uploaded_file = st.file_uploader("画像をアップロードしてください", type=["jpg"])
            if uploaded_file is not None:
                  imageList.append("アップロードされた画像")
            if os.path.isfile(IMAGE_FILE):
                  imageList.append("画像生成モードで生成された画像")
            
            selectImage = st.selectbox("コード進行を提案してもらう画像", imageList)
            if selectImage is not None:
                  if selectImage == "アップロードされた画像":
                        loadImage = uploaded_file
                  elif selectImage == "画像生成モードで生成された画像":
                        loadImage = IMAGE_FILE
                  image = Image.open(loadImage)
                  st.image(image)

            # 実行ボタン
            if st.button('コード進行作成', disabled = (loadImage == "NoImage")):
                  if loadImage != "NoImage":
                        with st.spinner('画像解析中...'):
                              # 画像を一時的なファイルに保存
                              if loadImage == uploaded_file:
                                    with open(IMAGE_TMP_FILE, "wb") as f:
                                          f.write(uploaded_file.getbuffer())
                              elif loadImage == IMAGE_FILE:
                                    shutil.copy(IMAGE_FILE, IMAGE_TMP_FILE)

                              base64_image = encode_image(IMAGE_TMP_FILE)
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
                                    temperature = 0.6
                              )
                        st.session_state.chordProgression = response.choices[0].message.content
                        
            if st.session_state.chordProgression != "":
                  # 結果の表示
                  st.success(st.session_state.chordProgression, icon="🎹")
                  #print(response.choices[0].message.content)

if __name__ == "__main__":
      main()
