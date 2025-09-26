from PIL import Image
import os

print("最強アイテムの画像を生成します...")
assets_path = 'assets'
os.makedirs(assets_path, exist_ok=True)

# 色の定義
BG = (0,0,0,0); YL = (255,215,0,255); YD = (184,134,11,255); WH = (255,255,255,255); RD=(255,0,0,255)

# 聖なる手榴弾のピクセルデータ
holy_grenade_data = [
    [BG,BG,BG,BG,BG,BG,RD,RD,BG,BG,BG,BG],
    [BG,BG,BG,BG,RD,RD,RD,RD,RD,RD,BG,BG],
    [BG,BG,BG,BG,BG,YL,YL,YL,YL,BG,BG,BG],
    [BG,BG,BG,YL,YL,YD,YL,YD,YL,YL,BG,BG],
    [BG,BG,YL,YL,YD,YL,YL,YL,YD,YL,YL,BG],
    [BG,YL,YL,YD,YL,YL,YL,YL,YL,YD,YL,YL],
    [BG,YL,YL,YL,YL,YD,WH,YD,YL,YL,YL,YL],
    [BG,YL,YL,YD,YL,YL,YL,YL,YL,YD,YL,YL],
    [BG,BG,YL,YL,YL,YD,YD,YD,YL,YL,YL,BG],
    [BG,BG,BG,YL,YL,YL,YL,YL,YL,YL,BG,BG],
    [BG,BG,BG,BG,YL,YL,YL,YL,YL,BG,BG,BG],
    [BG,BG,BG,BG,BG,YD,YD,YD,YD,BG,BG,BG],
]

def create_image_from_data(data, filename):
    TILE_SIZE = 48 # main.pyとサイズを合わせる
    height = len(data); width = len(data[0])
    img = Image.new('RGBA', (width, height))
    for y in range(height):
        for x in range(width):
            img.putpixel((x, y), data[y][x])
    img = img.resize((TILE_SIZE, TILE_SIZE), Image.NEAREST)
    filepath = os.path.join(assets_path, filename)
    img.save(filepath)
    print(f"'{filepath}' を生成しました。")

create_image_from_data(holy_grenade_data, "holy_grenade.png")
print("画像の生成が完了しました。")