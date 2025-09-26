from PIL import Image
import os

print("ボムの画像を生成します...")
assets_path = 'assets'
os.makedirs(assets_path, exist_ok=True)

# 色の定義
BG=(0,0,0,0); BL=(40,40,40,255); BD=(10,10,10,255); WH=(255,255,255,255)
FU=(210,180,140,255); YL=(255,255,0,255)

# ボムのピクセルデータ
bomb_data = [
    [BG,BG,BG,BG,FU,FU,FU,BG,BG,BG],
    [BG,BG,BG,FU,FU,YL,FU,FU,BG,BG],
    [BG,BG,BG,BG,FU,YL,FU,BG,BG,BG],
    [BG,BG,BL,BL,BL,BL,BL,BL,BG,BG],
    [BG,BL,BL,BD,BD,WH,BL,BL,BL,BG],
    [BG,BL,BD,BD,BL,BL,BL,BL,BL,BL],
    [BL,BL,BD,BL,BL,BL,BL,BL,BL,BL],
    [BL,BL,BL,BL,BL,BL,BL,BL,BD,BL],
    [BG,BL,BL,BL,BL,BL,BL,BD,BD,BL],
    [BG,BG,BL,BL,BL,BL,BL,BL,BL,BG],
]

def create_image_from_data(data, filename):
    TILE_SIZE = 48
    height = len(data); width = len(data[0])
    img = Image.new('RGBA', (width, height))
    for y in range(height):
        for x in range(width):
            img.putpixel((x, y), data[y][x])
    img = img.resize((TILE_SIZE, TILE_SIZE), Image.NEAREST)
    filepath = os.path.join(assets_path, filename)
    img.save(filepath)
    print(f"'{filepath}' を生成しました。")

create_image_from_data(bomb_data, "bomb.png")
print("画像の生成が完了しました。")