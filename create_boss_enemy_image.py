from PIL import Image
import os

print("巨大なボス画像を生成します...")
assets_path = 'assets'
os.makedirs(assets_path, exist_ok=True)

# 色の定義
BG=(0,0,0,0); GL=(112,128,144,255); GD=(47,79,79,255); EY=(255,255,0,255); PU=(0,0,0,255)

# 96x96のゴーレムのデータ
golem_data = [
    [BG]*18 + [GL]*60 + [BG]*18,
    [BG]*16 + [GL]*64 + [BG]*16,
    [BG]*14 + [GL]*68 + [BG]*14,
    [BG]*12 + [GL]*4 + [GD]*8 + [GL]*12 + [GD]*8 + [GL]*28 + [BG]*12,
    [BG]*12 + [GL]*2 + [GD]*10 + [GL]*10 + [GD]*10 + [GL]*26 + [BG]*12,
    [BG]*10 + [GL]*2 + [GD]*12 + [GL]*8 + [GD]*12 + [GL]*24 + [BG]*10,
    [BG]*10 + [GL]*1 + [GD]*14 + [GL]*6 + [GD]*14 + [GL]*23 + [BG]*10,
    [BG]*10 + [GD]*16 + [GL]*4 + [GD]*16 + [GL]*22 + [BG]*10,
    [BG]*10 + [GD]*16 + [GL]*2 + [GD]*16 + [GL]*24 + [BG]*10,
    [BG]*10 + [GD]*8 + [EY]*4 + [GD]*4 + [GL]*2 + [GD]*4 + [EY]*4 + [GD]*8 + [GL]*24 + [BG]*10,
    [BG]*10 + [GD]*7 + [EY]*6 + [GD]*3 + [GL]*2 + [GD]*3 + [EY]*6 + [GD]*7 + [GL]*23 + [BG]*10,
    [BG]*12 + [GD]*5 + [EY]*3 + [PU]*2 + [EY]*3 + [GD]*4 + [GD]*4 + [EY]*3 + [PU]*2 + [EY]*3 + [GD]*5 + [GL]*20 + [BG]*12,
    [BG]*12 + [GD]*5 + [EY]*2 + [PU]*4 + [EY]*2 + [GD]*4 + [GD]*4 + [EY]*2 + [PU]*4 + [EY]*2 + [GD]*5 + [GL]*20 + [BG]*12,
    [BG]*12 + [GD]*5 + [EY]*3 + [PU]*2 + [EY]*3 + [GD]*4 + [GD]*4 + [EY]*3 + [PU]*2 + [EY]*3 + [GD]*5 + [GL]*20 + [BG]*12,
    [BG]*12 + [GD]*7 + [EY]*6 + [GD]*3 + [GD]*3 + [EY]*6 + [GD]*7 + [GL]*22 + [BG]*12,
    [BG]*14 + [GD]*8 + [EY]*4 + [GD]*2 + [GD]*2 + [EY]*4 + [GD]*8 + [GL]*20 + [BG]*14,
    [BG]*14 + [GD]*16 + [GD]*16 + [GL]*18 + [BG]*14,
    [BG]*16 + [GD]*32 + [GL]*16 + [BG]*16,
    [BG]*16 + [GL]*2 + [GD]*30 + [GL]*16 + [BG]*16,
    [BG]*18 + [GL]*2 + [GD]*28 + [GL]*14 + [BG]*18,
    [BG]*18 + [GL]*4 + [GD]*12 + [PU]*2 + [GD]*12 + [GL]*12 + [BG]*18,
    [BG]*20 + [GL]*4 + [GD]*8 + [PU]*6 + [GD]*8 + [GL]*10 + [BG]*20,
    [BG]*20 + [GL]*6 + [GD]*4 + [PU]*10 + [GD]*4 + [GL]*8 + [BG]*20,
    [BG]*22 + [GL]*6 + [PU]*12 + [GL]*6 + [BG]*22,
    [BG]*22 + [GL]*8 + [PU]*8 + [GL]*8 + [BG]*22,
    [BG]*24 + [GL]*24 + [BG]*24,
]
# データを96x96に拡張
full_golem_data = [[BG]*96 for _ in range(96)]
for y, row in enumerate(golem_data):
    for x, color in enumerate(row):
        if y*2 < 96 and x*2 < 96:
            full_golem_data[y*2+20][x*2+0] = color
            full_golem_data[y*2+20][x*2+1] = color
            full_golem_data[y*2+21][x*2+0] = color
            full_golem_data[y*2+21][x*2+1] = color

def create_image_from_data(data, filename):
    img = Image.new('RGBA', (len(data[0]), len(data)))
    for y, row in enumerate(data):
        for x, color in enumerate(row):
            img.putpixel((x, y), color)
    filepath = os.path.join(assets_path, filename)
    img.save(filepath)
    print(f"'{filepath}' を生成しました。")

create_image_from_data(full_golem_data, "golem.png")
print("画像の生成が完了しました。")