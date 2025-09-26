from PIL import Image
import os

print("アイテム画像を生成します...")
assets_path = 'assets'
os.makedirs(assets_path, exist_ok=True)

# 色の定義 (R, G, B, A)
BG = (0,0,0,0); PT = (255,105,180,255); PK = (220,20,60,255); WH = (255,255,255,255)
RC = (169,169,169,255); RK = (105,105,105,255)

# ★★★ ここにTILE_SIZEの定義を追加 ★★★
TILE_SIZE = 48

# ポーションのピクセルデータ
potion_data = [
    [BG,BG,BG,BG,BG,BG,PK,PK,BG,BG,BG,BG,BG,BG],
    [BG,BG,BG,BG,PK,PK,WH,WH,PK,PK,BG,BG,BG,BG],
    [BG,BG,BG,BG,PK,PT,PT,PT,PT,PK,BG,BG,BG,BG],
    [BG,BG,BG,PK,PT,PT,PT,PT,PT,PT,PK,BG,BG,BG],
    [BG,BG,BG,PK,PT,PT,WH,PT,PT,PT,PK,BG,BG,BG],
    [BG,BG,BG,PK,PT,PT,PT,PT,PT,PT,PK,BG,BG,BG],
    [BG,BG,BG,PK,PT,PT,PT,PT,PT,PT,PK,BG,BG,BG],
    [BG,BG,BG,BG,PK,PT,PT,PT,PT,PK,BG,BG,BG,BG],
    [BG,BG,BG,BG,BG,PK,PK,PK,PK,BG,BG,BG,BG,BG],
]

# 石のピクセルデータ
rock_data = [
    [BG,BG,BG,BG,RC,RC,RC,BG,BG,BG],
    [BG,BG,RC,RC,RK,RC,RC,RC,BG,BG],
    [BG,RC,RC,RK,RC,RC,RC,RC,RC,BG],
    [BG,RC,RK,RC,RC,RC,RK,RC,RC,RC],
    [RC,RC,RC,RC,RK,RC,RC,RC,RK,RC],
    [RC,RK,RC,RC,RC,RC,RK,RC,RC,BG],
    [BG,RC,RC,RK,RC,RC,RC,RC,BG,BG],
    [BG,BG,RC,RC,RK,RC,RC,BG,BG,BG],
]

def create_image_from_data(data, filename, tile_size):
    height = len(data); width = len(data[0])
    img = Image.new('RGBA', (width, height))
    for y in range(height):
        for x in range(width):
            img.putpixel((x, y), data[y][x])
    # ゲーム内のタイルサイズに合わせて拡大
    img = img.resize((tile_size, tile_size), Image.NEAREST) # NEARESTはドット絵の拡大に適している
    filepath = os.path.join(assets_path, filename)
    img.save(filepath)
    print(f"'{filepath}' を生成しました。")

# 48x48のサイズで画像を生成
create_image_from_data(potion_data, "potion.png", TILE_SIZE)
create_image_from_data(rock_data, "rock.png", TILE_SIZE)

print("画像の生成が完了しました。")

