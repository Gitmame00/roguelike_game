import pygame
import sys
import os
import random
import math
from collections import deque # For BFS

# 1. 初期設定と準備
# ------------------------------------
pygame.init()
TILE_SIZE, MAP_WIDTH, MAP_HEIGHT, UI_PANEL_HEIGHT = 48, 25, 15, 60
SCREEN_WIDTH, SCREEN_HEIGHT = TILE_SIZE*MAP_WIDTH, TILE_SIZE*MAP_HEIGHT + UI_PANEL_HEIGHT
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("ポッチの冒険 - Final Fix")
clock = pygame.time.Clock()
font, big_font = pygame.font.Font(None, 24), pygame.font.Font(None, 74)

# 色
C = {
    "BLACK": (0,0,0), "FLOOR": (120,90,40), "WALL": (60,40,20), "WHITE": (255,255,255),
    "UI": (40,40,40), "BUTTON": (180,50,50), "HP_BAR": (0,200,0), "HP_BAR_BG": (80,0,0),
    "XP_BAR": (0,150,200), "XP_BAR_BG": (0,0,80), "TARGET": (255,0,0,150), "RANGE": (0,100,255,80),
    "RESTART_BUTTON": (50, 180, 50),
    "PATH_HIGHLIGHT": (0, 255, 255, 50) # パス視覚化用の色を追加
}

# ゲームステート定数
PLAYER_INPUT = "player_input"
PLAYER_MOVING = "player_moving" # 新しいステート
ENEMY_TURN = "enemy_turn"
PROJECTILE_ANIMATION = "projectile_animation"
TARGETING = "targeting"
SCREEN_FLASH = "screen_flash"
GAME_OVER = "game_over"
NEW_FLOOR = "new_floor"

# 画像読み込み
assets_path = 'assets'
try:
    images = {
        "pocchi": [pygame.image.load(os.path.join(assets_path, f'pocchi_{i}.png')).convert_alpha() for i in [1,2]],
        "goblin": pygame.image.load(os.path.join(assets_path, 'goblin.png')).convert_alpha(),
        "orc": pygame.image.load(os.path.join(assets_path, 'orc.png')).convert_alpha(),
        "golem": pygame.image.load(os.path.join(assets_path, 'golem.png')).convert_alpha(),
        "potion": pygame.image.load(os.path.join(assets_path, 'potion.png')).convert_alpha(),
        "rock": pygame.image.load(os.path.join(assets_path, 'rock.png')).convert_alpha(),
        "holy_grenade": pygame.image.load(os.path.join(assets_path, 'holy_grenade.png')).convert_alpha(),
        "bomb": pygame.image.load(os.path.join(assets_path, 'bomb.png')).convert_alpha(),
        "rock_projectile": pygame.image.load(os.path.join(assets_path, 'rock_projectile.png')).convert_alpha(),
        "stair": pygame.Surface((TILE_SIZE, TILE_SIZE))
    }
    images["stair"].fill((150,0,150))
except pygame.error as e:
    print(f"エラー: 'assets'フォルダの画像読み込みに失敗しました。: {e}"); sys.exit()

# 2. クラスの定義
# ------------------------------------
class Entity:
    def __init__(self, x, y, image, hp, name, attack=10):
        self.x, self.y, self.image, self.hp, self.max_hp, self.name, self.attack = x, y, image, hp, hp, name, attack
    def move(self, dx, dy, dungeon_map, entities):
        new_x, new_y = self.x + dx, self.y + dy
        is_occupied = any(e.x==new_x and e.y==new_y for e in entities if e is not self and not isinstance(e, Boss))
        # ボスは2x2なので特別な衝突判定
        boss_collision = any(b.x<=new_x<b.x+2 and b.y<=new_y<b.y+2 for b in entities if isinstance(b, Boss))
        if dungeon_map[new_y][new_x] == 0 and not is_occupied and not boss_collision:
            self.x, self.y = new_x, new_y
            return True # 成功した移動
        return False # 失敗した移動
    def draw(self, surface):
        hp_bar_w = int(TILE_SIZE * (self.hp/self.max_hp)) if self.max_hp > 0 else 0
        pygame.draw.rect(surface, C["HP_BAR_BG"], (self.x*TILE_SIZE, self.y*TILE_SIZE-10, TILE_SIZE, 5))
        pygame.draw.rect(surface, C["HP_BAR"], (self.x*TILE_SIZE, self.y*TILE_SIZE-10, hp_bar_w, 5))
        rect = self.image.get_rect(center=(self.x*TILE_SIZE + TILE_SIZE//2, self.y*TILE_SIZE + TILE_SIZE//2))
        surface.blit(self.image, rect)

class Player(Entity):
    def __init__(self, x, y, image_dict):
        super().__init__(x, y, image_dict["pocchi"][0], 100, "Player", attack=20)
        self.p_images = image_dict["pocchi"]
        self.current_frame, self.animation_timer = 0, 0
        self.inventory, self.max_inventory = [], 5
        self.level, self.xp, self.xp_to_next = 1, 0, 100
        self.item_to_throw = None
        self.target_path = [] # 連続移動の目標パスを保存するリストを追加
        self.target_enemy = None # 移動後に攻撃する敵を保存

    def update_animation(self):
        self.animation_timer = (self.animation_timer + 1) % 21
        if self.animation_timer == 20: self.current_frame = (self.current_frame+1)%len(self.p_images); self.image = self.p_images[self.current_frame]
    def add_xp(self, amount):
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.level += 1; self.xp -= self.xp_to_next; self.xp_to_next = int(self.xp_to_next * 1.5)
            self.max_hp += 20; self.hp = self.max_hp; self.attack += 5

class Enemy(Entity):
    def __init__(self, x, y, image, hp, name, attack, points):
        super().__init__(x, y, image, hp, name, attack); self.points = points
    def take_turn(self, player, dungeon_map, entities):
        dist = math.hypot(self.x-player.x, self.y-player.y)
        if dist < 8:
            if dist <= 1.5: player.hp -= self.attack
            else: dx=1 if player.x>self.x else -1 if player.x<self.x else 0; dy=1 if player.y>self.y else -1 if player.y<self.y else 0; self.move(dx,dy,dungeon_map,entities)

class RangedEnemy(Enemy):
    def take_turn(self, player, dungeon_map, entities, projectiles):
        dist = math.hypot(self.x - player.x, self.y - player.y)
        dx = 1 if player.x > self.x else -1 if player.x < self.x else 0
        dy = 1 if player.y > self.y else -1 if player.y < self.y else 0
        
        # プレイヤーが縦か横の直線状にいるかチェック
        is_in_line_of_sight = (self.x == player.x or self.y == player.y)
        
        if is_in_line_of_sight and 1 < dist < 6:
            # 直線状かつ射程範囲内なら攻撃
            projectiles.append(Projectile(self.x, self.y, player.x, player.y, images["rock_projectile"], self.attack))
        elif dist <= 2:
            # 近づきすぎたら、プレイヤーのいない方向へ下がる
            self.move(-dx, -dy, dungeon_map, entities)
        elif dist < 8:
            # 遠すぎたら、プレイヤーに近づく
            self.move(dx, dy, dungeon_map, entities)

class Projectile:
    def __init__(self, start_x, start_y, target_x, target_y, image, damage):
        self.x, self.y = start_x*TILE_SIZE+TILE_SIZE//2, start_y*TILE_SIZE+TILE_SIZE//2
        self.image, self.damage = image, damage
        angle = math.atan2(target_y-start_y, target_x-start_x)
        self.vx, self.vy = math.cos(angle)*15, math.sin(angle)*15; self.target_pos = (target_x, target_y)
    def update(self):
        self.x+=self.vx; self.y+=self.vy
        if math.hypot(self.x-(self.target_pos[0]*TILE_SIZE+TILE_SIZE//2), self.y-(self.target_pos[1]*TILE_SIZE+TILE_SIZE//2)) < 20: return True
        return False
    def draw(self, surface): surface.blit(self.image, self.image.get_rect(center=(int(self.x), int(self.y))))

class Boss(Enemy):
    def __init__(self, x, y): super().__init__(x, y, images["golem"], 300, "Stone Golem", 30, 1000)
    def take_turn(self, player, dungeon_map, entities):
        in_range = (self.x-1<=player.x<self.x+3) and (self.y-1<=player.y<self.y+3)
        if in_range: player.hp-=self.attack
        elif math.hypot((self.x+0.5)-player.x, (self.y+0.5)-player.y) < 8:
            dx=1 if player.x>self.x+0.5 else -1 if player.x<self.x+0.5 else 0; dy=1 if player.y>self.y+0.5 else -1 if player.y<self.y+0.5 else 0; self.move(dx,dy,dungeon_map,entities)
    def move(self, dx, dy, dungeon_map, entities):
        nx,ny=self.x+dx,self.y+dy; can_move=True
        for i in range(2):
            for j in range(2):
                # ボスは2x2なので4つのタイル全てをチェック
                if not(0<=ny+j<MAP_HEIGHT and 0<=nx+i<MAP_WIDTH)or dungeon_map[ny+j][nx+i]!=0 or any(e.x==nx+i and e.y==ny+j for e in entities if e is not self): can_move=False; break
            if not can_move: break
        if can_move: self.x, self.y = nx, ny; return True
        return False
    def draw(self, surface):
        hp_w=int(TILE_SIZE*2*(self.hp/self.max_hp))if self.max_hp>0 else 0
        pygame.draw.rect(surface,C["HP_BAR_BG"],(self.x*TILE_SIZE,self.y*TILE_SIZE-10,TILE_SIZE*2,10)); pygame.draw.rect(surface,C["HP_BAR"],(self.x*TILE_SIZE,self.y*TILE_SIZE-10,hp_w,10))
        surface.blit(self.image,(self.x*TILE_SIZE,self.y*TILE_SIZE))

class Item:
    def __init__(self,x,y,image,name): self.x,self.y,self.image,self.name=x,y,image,name
    def draw(self,surface): surface.blit(self.image,(self.x*TILE_SIZE,self.y*TILE_SIZE))
class Room:
    def __init__(self,x,y,w,h): self.x1,self.y1,self.x2,self.y2=x,y,x+w,y+h
    def center(self): return ((self.x1+self.x2)//2,(self.y1+self.y2)//2)
    def intersects(self,other): return (self.x1<=other.x2+1 and self.x2>=other.x1-1 and self.y1<=other.y2+1 and self.y2>=other.y1-1)

# パス探索ユーティリティ関数 (BFS)
def find_path(start_x, start_y, target_x, target_y, dungeon_map, obstacles):
    q = deque()
    q.append(((start_x, start_y), [])) # (現在の位置, 現在の位置までのパス)
    visited = set()
    visited.add((start_x, start_y))

    while q:
        (cx, cy), path = q.popleft()

        if (cx, cy) == (target_x, target_y):
            return path
        
        # 8方向移動
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
            nx, ny = cx + dx, cy + dy

            # マップ範囲チェック
            if not (0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT):
                continue
            
            # 壁チェック
            if dungeon_map[ny][nx] == 1:
                continue
            
            # 障害物チェック
            is_occupied = False
            for e in obstacles:
                if isinstance(e, Boss):
                    if e.x <= nx < e.x + 2 and e.y <= ny < e.y + 2:
                        is_occupied = True
                        break
                else: # 通常の敵
                    if e.x == nx and e.y == ny:
                        is_occupied = True
                        break
            
            if is_occupied:
                continue

            if (nx, ny) not in visited:
                visited.add((nx, ny))
                q.append(((nx, ny), path + [(nx, ny)]))
    
    return [] # パスが見つからなかった場合

# 敵の隣接セルへのパスを検索するヘルパー関数
def find_path_to_adjacent_of_enemy(start_x, start_y, target_enemy, dungeon_map, all_entities):
    # プレイヤー以外の全てのエンティティを障害物として扱う
    obstacles_for_pathfinding = [e for e in all_entities if e is not player and e is not target_enemy] # ターゲット敵自体は直接の障害物ではないが、その周囲へのパスを探す

    adjacent_empty_tiles = []
    
    if isinstance(target_enemy, Boss):
        # ボスの周囲8方向と、ボスの4隅の隣接タイルをチェック
        for y_offset in range(-1, 3): # ボスのY座標から上下に1タイルずつ広がる範囲
            for x_offset in range(-1, 3): # ボスのX座標から左右に1タイルずつ広がる範囲
                test_x, test_y = target_enemy.x + x_offset, target_enemy.y + y_offset
                if (0 <= test_x < MAP_WIDTH and 0 <= test_y < MAP_HEIGHT and
                    dungeon_map[test_y][test_x] == 0): # フロアタイルであること
                    # ボスの占有タイルではないことを確認
                    if not (target_enemy.x <= test_x < target_enemy.x + 2 and
                            target_enemy.y <= test_y < target_enemy.y + 2):
                        adjacent_empty_tiles.append((test_x, test_y))
    else: # 1x1 の敵
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
            test_x, test_y = target_enemy.x + dx, target_enemy.y + dy
            if (0 <= test_x < MAP_WIDTH and 0 <= test_y < MAP_HEIGHT and
                dungeon_map[test_y][test_x] == 0): # フロアタイルであること
                adjacent_empty_tiles.append((test_x, test_y))
    
    shortest_path = []
    min_len = float('inf')

    # 各隣接する空きタイルへのパスを探し、最短のものを選択
    for adj_x, adj_y in adjacent_empty_tiles:
        path = find_path(start_x, start_y, adj_x, adj_y, dungeon_map, obstacles_for_pathfinding + [target_enemy]) # find_path にはターゲット敵も障害物として渡す
        if path and len(path) < min_len:
            min_len = len(path)
            shortest_path = path
            
    return shortest_path

# 3. マップ生成
def generate_dungeon(width, height, floor, bosses_defeated):
    if floor > 0 and floor % 5 == 0: return generate_boss_floor(width, height)
    if floor > 1 and random.random() < 0.15: return generate_monster_house(width, height, floor, bosses_defeated)
    dungeon_map=[[1 for _ in range(width)]for _ in range(height)]; rooms=[]
    MAX_ROOMS,MIN_SIZE,MAX_SIZE=12,4,7
    for _ in range(MAX_ROOMS*10):
        # 修正箇所
        w = random.randint(MIN_SIZE, MAX_SIZE)
        h = random.randint(MIN_SIZE, MAX_SIZE)
        x = random.randint(1, width - w - 2)
        y = random.randint(1, height - h - 2)
        new_room=Room(x,y,w,h)
        if not any(new_room.intersects(r)for r in rooms):
            for ry in range(new_room.y1,new_room.y2):
                for rx in range(new_room.x1,new_room.x2):dungeon_map[ry][rx]=0
            rooms.append(new_room)
        if len(rooms)>=MAX_ROOMS: break
    connected={0}
    while len(connected)<len(rooms):
        min_dist=float('inf'); pair=(None,None)
        for i in sorted(list(connected)):
            for j in range(len(rooms)):
                if j not in connected:
                    dist=math.hypot(rooms[i].center()[0]-rooms[j].center()[0],rooms[i].center()[1]-rooms[j].center()[1])
                    if dist<min_dist: min_dist=dist; pair=(i,j)
        if pair[0] is None: break
        r1,r2=rooms[pair[0]],rooms[pair[1]]; px,py=r1.center(); nx,ny=r2.center()
        if random.randint(0,1)==0:
            for tx in range(min(px,nx),max(px,nx)+1): dungeon_map[py][tx]=0
            for ty in range(min(py,ny),max(py,ny)+1): dungeon_map[ty][nx]=0
        else:
            for ty in range(min(py,ny),max(py,ny)+1): dungeon_map[ty][px]=0
            for tx in range(min(px,nx),max(px,nx)+1): dungeon_map[ny][tx]=0
        connected.add(pair[1])
    entities=[]; buff=1.05**bosses_defeated
    for r in rooms[1:]:
        if random.random()<0.5+floor*0.02:
            enemy_type = random.random()
            if enemy_type < 0.2 + floor*0.05: entities.append(Enemy(r.center()[0],r.center()[1],images["orc"],int(50*buff),"Orc",int(15*buff),int(100*buff)))
            elif enemy_type < 0.5: entities.append(RangedEnemy(r.center()[0],r.center()[1],images["goblin"],int(25*buff),"Goblin Slinger",int(10*buff),int(60*buff)))
            else: entities.append(Enemy(r.center()[0],r.center()[1],images["goblin"],int(30*buff),"Goblin",int(10*buff),int(50*buff)))
    items=[]
    for r in rooms:
        if random.random()<0.1: items.append(Item(r.center()[0]+1,r.center()[1],images["potion"],"Potion"))
        if random.random()<0.2: items.append(Item(r.center()[0]-1,r.center()[1],images["rock"],"Rock"))
        if random.random()<0.07: items.append(Item(r.center()[0],r.center()[1]+1,images["bomb"],"Bomb"))
        if random.random()<0.05: items.append(Item(r.center()[0],r.center()[1]+1,images["holy_grenade"],"Holy Grenade"))
    start_room = rooms[0]
    farthest_room = max(rooms,key=lambda r: math.hypot(start_room.center()[0]-r.center()[0],start_room.center()[1]-r.center()[1]))
    stair_pos = farthest_room.center()
    return dungeon_map,rooms[0].center(),entities,items,stair_pos,True
def generate_boss_floor(width, height):
    dungeon_map=[[1 for _ in range(width)]for _ in range(height)]; room=Room(3,3,width-6,height-6)
    for y in range(room.y1,room.y2):
        for x in range(room.x1,room.x2): dungeon_map[y][x]=0
    player_start=(room.center()[0],room.y2-2); boss=Boss(room.center()[0]-1,room.y1+1); stair_pos=room.center()
    return dungeon_map,player_start,[boss],[],stair_pos,True
def generate_monster_house(width, height, floor, bosses_defeated):
    dungeon_map, player_start, _, _, stair_pos, _ = generate_boss_floor(width, height)
    entities=[]; buff=1.05**bosses_defeated; room=Room(3,3,width-6,height-6)
    num_enemies = random.randint(8, 12)
    for _ in range(num_enemies):
        ex, ey = random.randint(room.x1,room.x2-1), random.randint(room.y1,room.y2-1)
        if (ex,ey) != player_start and not any(e.x==ex and e.y==ey for e in entities):
            enemy_type = random.random()
            if enemy_type < 0.3: entities.append(RangedEnemy(ex, ey, images["goblin"], int(25*buff), "Goblin Slinger", int(10*buff), int(60*buff)))
            elif enemy_type < 0.6: entities.append(Enemy(ex,ey,images["orc"],int(50*buff),"Orc",int(15*buff),int(100*buff)))
            else: entities.append(Enemy(ex,ey,images["goblin"],int(30*buff),"Goblin",int(10*buff),int(50*buff)))
    return dungeon_map,player_start,entities,[],stair_pos,False
def load_highscore():
    try:
        with open("highscore.txt","r") as f: return int(f.read())
    except(FileNotFoundError,ValueError): return 0
def save_highscore(score):
    with open("highscore.txt","w") as f: f.write(str(score))

# ヘルパー関数: プレイヤーがエンティティに隣接しているかチェック
def is_player_adjacent_to_entity(player_obj, entity):
    if isinstance(entity, Boss):
        for bx_offset in range(2):
            for by_offset in range(2):
                if math.hypot(player_obj.x - (entity.x + bx_offset), player_obj.y - (entity.y + by_offset)) <= 1.5:
                    return True
        return False
    else: # 1x1 enemy
        return math.hypot(player_obj.x - entity.x, player_obj.y - entity.y) <= 1.5

# 4. ゲームのメインループ
# ------------------------------------
def main():
    player = Player(0, 0, images)
    game_state, floor_number, score, bosses_defeated = NEW_FLOOR, 0, 0, 0 # 初期ステートをNEW_FLOORに
    high_score = load_highscore()
    dungeon_map, enemies, items, stair_pos = [],[],[],(0,0)
    projectiles = []
    exit_button_rect = pygame.Rect(SCREEN_WIDTH-110,SCREEN_HEIGHT-50,100,40)
    inventory_rects = [pygame.Rect(650+i*50,SCREEN_HEIGHT-55,TILE_SIZE,TILE_SIZE) for i in range(player.max_inventory)]
    restart_button_rect = pygame.Rect(SCREEN_WIDTH/2-100,SCREEN_HEIGHT/2+50,200,50)
    stairs_visible = True; flash_timer = 0
    
    # メインループ
    while True:
        if game_state == NEW_FLOOR:
            floor_number += 1
            dungeon_map,start_pos,enemies,items,stair_pos,stairs_visible = generate_dungeon(MAP_WIDTH,MAP_HEIGHT,floor_number,bosses_defeated)
            player.x, player.y = start_pos; 
            player.target_path = [] # 新しいフロアになったらパスをクリア
            player.target_enemy = None # ターゲット敵もクリア
            game_state = PLAYER_INPUT # 新しいフロアではプレイヤー入力待ちから開始
        
        if player.hp <= 0: 
            game_state = GAME_OVER
            if score > high_score: save_highscore(score); high_score = score # ゲームオーバー時にスコアを保存

        all_entities = [player] + enemies # 全てのエンティティを更新

        # イベント処理
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()

            if game_state == GAME_OVER:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if restart_button_rect.collidepoint(event.pos):
                        player = Player(0,0, images) # プレイヤーを初期化
                        game_state, floor_number, score, bosses_defeated = NEW_FLOOR, 0, 0, 0
                        high_score = load_highscore() # ハイスコアを再度ロード
                        continue
                    if exit_button_rect.collidepoint(event.pos): pygame.quit(); sys.exit()
            
            # プレイヤー入力待ち状態
            elif game_state == PLAYER_INPUT:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if exit_button_rect.collidepoint(event.pos): pygame.quit(); sys.exit()
                    mouse_x, mouse_y = event.pos
                    
                    # UIパネルの操作
                    if mouse_y >= SCREEN_HEIGHT-UI_PANEL_HEIGHT:
                        for i,rect in enumerate(inventory_rects):
                            if rect.collidepoint(mouse_x,mouse_y) and i<len(player.inventory):
                                item = player.inventory[i]
                                if item.name == "Potion":
                                    if player.hp<player.max_hp: 
                                        player.hp=min(player.max_hp,player.hp+40); player.inventory.pop(i); 
                                        game_state = ENEMY_TURN # ポーション使用はターン消費
                                elif item.name in ["Rock", "Holy Grenade"]:
                                    game_state = TARGETING # ターゲティング開始
                                    player.item_to_throw = i
                                elif item.name == "Bomb":
                                    # Bombは全ての敵に影響し、ターンを消費する
                                    for e in enemies: e.hp -= 20
                                    enemies = [e for e in enemies if e.hp > 0] # 死んだ敵をフィルタリング
                                    player.inventory.pop(i); game_state = SCREEN_FLASH; flash_timer = pygame.time.get_ticks()
                                    # SCREEN_FLASH の後 ENEMY_TURN に遷移
                        continue # UIがクリックされた場合はマップ操作をスキップ

                    # マップ操作（移動または攻撃）
                    tile_x, tile_y = mouse_x//TILE_SIZE, mouse_y//TILE_SIZE

                    # 有効なマップタイルがクリックされたか確認
                    if not (0 <= tile_x < MAP_WIDTH and 0 <= tile_y < MAP_HEIGHT):
                        player.target_path = []; player.target_enemy = None
                        continue

                    # クリックされた位置に敵がいるかチェック
                    clicked_enemy = None
                    for e in enemies:
                        if isinstance(e, Boss):
                            if e.x <= tile_x < e.x + 2 and e.y <= tile_y < e.y + 2:
                                clicked_enemy = e
                                break
                        else: # 1x1 の敵
                            if e.x == tile_x and e.y == tile_y:
                                clicked_enemy = e
                                break
                    
                    if clicked_enemy:
                        # ターゲットが敵の場合
                        if is_player_adjacent_to_entity(player, clicked_enemy):
                            # プレイヤーがすでに隣接している場合、直接攻撃
                            clicked_enemy.hp -= player.attack
                            if clicked_enemy.hp <= 0:
                                if isinstance(clicked_enemy, Boss): bosses_defeated += 1
                                enemies.remove(clicked_enemy); score += clicked_enemy.points; player.add_xp(clicked_enemy.points)
                            player.target_path = [] # 既存のパスをクリア
                            player.target_enemy = None
                            game_state = ENEMY_TURN # 攻撃でターン消費
                        else:
                            # 敵が隣接していない場合、敵の隣接セルへのパスを計算
                            path_to_adj = find_path_to_adjacent_of_enemy(player.x, player.y, clicked_enemy, dungeon_map, all_entities)
                            if path_to_adj:
                                player.target_path = path_to_adj
                                player.target_enemy = clicked_enemy # ターゲット敵を設定
                                game_state = PLAYER_MOVING # 自動移動開始
                            else:
                                player.target_path = []; player.target_enemy = None # パスが見つからなければ何もせずターン消費なし
                    else:
                        # ターゲットがフロアタイルまたは壁の場合
                        if dungeon_map[tile_y][tile_x] == 0: # フロアタイル
                            # フロアタイルへのパスを計算
                            path = find_path(player.x, player.y, tile_x, tile_y, dungeon_map, [e for e in all_entities if e is not player])
                            if path:
                                player.target_path = path
                                player.target_enemy = None # 敵はターゲットしない
                                game_state = PLAYER_MOVING # 自動移動開始
                            else:
                                player.target_path = []; player.target_enemy = None # パスが見つからなければ何もせずターン消費なし
                        elif (tile_x, tile_y) == (player.x, player.y): # 自分自身をクリックした場合
                            player.target_path = []; player.target_enemy = None # 自動移動を停止
                        # 壁をクリックした場合は何もせずターン消費なし

            elif game_state == TARGETING:
                 if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_x, mouse_y = event.pos; tile_x, tile_y = mouse_x//TILE_SIZE, mouse_y//TILE_SIZE
                    if tile_y < MAP_HEIGHT:
                        item = player.inventory[player.item_to_throw]
                        target_entity = None
                        for e in enemies:
                            if isinstance(e, Boss):
                                if e.x <= tile_x < e.x + 2 and e.y <= tile_y < e.y + 2:
                                    target_entity = e
                                    break
                            else:
                                if e.x == tile_x and e.y == tile_y:
                                    target_entity = e
                                    break
                        
                        if target_entity and math.hypot(player.x-tile_x, player.y-tile_y) <= 4:
                            damage = 9999 if item.name == "Holy Grenade" else 30
                            target_entity.hp -= damage
                            if target_entity.hp <= 0:
                                if isinstance(target_entity, Boss): bosses_defeated += 1
                                enemies.remove(target_entity); score += target_entity.points; player.add_xp(target_entity.points)
                            player.inventory.pop(player.item_to_throw); 
                            player.item_to_throw = None
                            game_state = ENEMY_TURN # アイテム使用でターン消費
                        else: 
                            game_state = PLAYER_INPUT # 無効なターゲットまたは射程外の場合、ターゲティングをキャンセルして入力待ちに戻る
                            player.item_to_throw = None
        
        # --- ゲームステートに基づく処理 ---
        if game_state == PLAYER_MOVING:
            if player.target_path:
                next_x, next_y = player.target_path[0]

                # 次のステップに敵がいるかチェック
                enemy_at_next_step = None
                for e in enemies:
                    if isinstance(e, Boss):
                        if e.x <= next_x < e.x + 2 and e.y <= next_y < e.y + 2:
                            enemy_at_next_step = e
                            break
                    else:
                        if e.x == next_x and e.y == next_y:
                            enemy_at_next_step = e
                            break

                if enemy_at_next_step:
                    # パスの次のタイルに敵がいる場合、移動を停止し攻撃
                    player.target_path = [] # 移動を停止
                    
                    # プレイヤーが敵に隣接しているか確認（ボスは複数タイル）
                    if is_player_adjacent_to_entity(player, enemy_at_next_step):
                         enemy_at_next_step.hp -= player.attack
                         if enemy_at_next_step.hp <= 0:
                            if isinstance(enemy_at_next_step, Boss): bosses_defeated += 1
                            enemies.remove(enemy_at_next_step); score += enemy_at_next_step.points; player.add_xp(enemy_at_next_step.points)
                    
                    player.target_enemy = None # ターゲット敵をクリア
                    game_state = ENEMY_TURN # 攻撃でターン消費
                else:
                    # 敵がいない場合、1ステップ移動
                    player.x, player.y = next_x, next_y
                    player.target_path.pop(0)

                    # 移動後にアイテム拾得をチェック
                    item_to_pick = next((i for i in items if i.x==player.x and i.y==player.y), None)
                    if item_to_pick and len(player.inventory)<player.max_inventory: player.inventory.append(item_to_pick); items.remove(item_to_pick)

                    # 階段に到達したかチェック
                    if player.x==stair_pos[0] and player.y==stair_pos[1] and stairs_visible: 
                        game_state = NEW_FLOOR # 新しいフロアへ
                    else: 
                        game_state = ENEMY_TURN # 1ステップ移動でターン消費
            else: 
                # パスが完了した場合、もしターゲット敵が設定されていれば攻撃
                if player.target_enemy and player.target_enemy in enemies and is_player_adjacent_to_entity(player, player.target_enemy):
                    player.target_enemy.hp -= player.attack
                    if player.target_enemy.hp <= 0:
                        if isinstance(player.target_enemy, Boss): bosses_defeated += 1
                        enemies.remove(player.target_enemy); score += player.target_enemy.points; player.add_xp(player.target_enemy.points)
                player.target_enemy = None # ターゲット敵をクリア
                game_state = ENEMY_TURN # パス完了でターン消費

        elif game_state == SCREEN_FLASH:
            if pygame.time.get_ticks() - flash_timer > 100: 
                game_state = ENEMY_TURN

        elif game_state == ENEMY_TURN:
            for enemy in enemies:
                if isinstance(enemy, RangedEnemy): enemy.take_turn(player, dungeon_map, all_entities, projectiles)
                else: enemy.take_turn(player, dungeon_map, all_entities)
            
            # 全ての敵が行動した後、発射物があれば解決
            if not projectiles:
                # 階段の表示条件を再チェック
                if not stairs_visible and not enemies: stairs_visible = True
                
                if player.target_path:
                    game_state = PLAYER_MOVING # パスが残っていれば自動移動を継続
                else:
                    game_state = PLAYER_INPUT # パスがなければプレイヤー入力待ちに戻る
            else: 
                game_state = PROJECTILE_ANIMATION

        elif game_state == PROJECTILE_ANIMATION:
            for p in projectiles[:]: # コピーを反復処理
                if p.update():
                    if p.target_pos == (player.x, player.y): player.hp -= p.damage
                    projectiles.remove(p)
            if not projectiles:
                # 階段の表示条件を再チェック
                if not stairs_visible and not enemies: stairs_visible = True
                
                if player.target_path:
                    game_state = PLAYER_MOVING # パスが残っていれば自動移動を継続
                else:
                    game_state = PLAYER_INPUT # パスがなければプレイヤー入力待ちに戻る

        player.update_animation()
        screen.fill(C["BLACK"])
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                rect=pygame.Rect(x*TILE_SIZE,y*TILE_SIZE,TILE_SIZE,TILE_SIZE); pygame.draw.rect(screen, C["WALL"] if dungeon_map[y][x]==1 else C["FLOOR"], rect)
        
        # プレイヤーのパスハイライト描画
        if player.target_path:
            for px, py in player.target_path:
                s = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                s.fill(C["PATH_HIGHLIGHT"])
                screen.blit(s, (px * TILE_SIZE, py * TILE_SIZE))

        # プレイヤーの移動または攻撃オプションの描画 (PLAYER_INPUT 状態でパスがない場合のみ)
        if game_state == PLAYER_INPUT and not player.target_path:
            for dy in range(-1,2):
                for dx in range(-1,2):
                    if dx==0 and dy==0: continue
                    tx,ty=player.x+dx,player.y+dy
                    if 0<=ty<MAP_HEIGHT and 0<=tx<MAP_WIDTH:
                        is_enemy=any(e.x<=tx<e.x+(2 if isinstance(e,Boss)else 1) and e.y<=ty<e.y+(2 if isinstance(e,Boss)else 1) for e in enemies)
                        rect=pygame.Rect(tx*TILE_SIZE,ty*TILE_SIZE,TILE_SIZE,TILE_SIZE)
                        if is_enemy: 
                            s=pygame.Surface((TILE_SIZE,TILE_SIZE),pygame.SRCALPHA);s.fill((255,0,0,80));screen.blit(s,rect.topleft);pygame.draw.rect(screen,(255,0,0),rect,2)
                        elif dungeon_map[ty][tx]!=1: 
                            s=pygame.Surface((TILE_SIZE,TILE_SIZE),pygame.SRCALPHA);s.fill((255,255,0,80));screen.blit(s,rect.topleft);pygame.draw.rect(screen,(255,255,0),rect,2)
        
        if stairs_visible: screen.blit(images["stair"], (stair_pos[0]*TILE_SIZE, stair_pos[1]*TILE_SIZE))
        for item in items: item.draw(screen)
        
        if game_state == TARGETING:
            for y in range(MAP_HEIGHT):
                for x in range(MAP_WIDTH):
                    if math.hypot(player.x-x, player.y-y)<=4 and dungeon_map[y][x]==0:
                        s=pygame.Surface((TILE_SIZE,TILE_SIZE),pygame.SRCALPHA);s.fill(C["RANGE"]);screen.blit(s,(x*TILE_SIZE,y*TILE_SIZE))
        
        for enemy in enemies: enemy.draw(screen)
        player.draw(screen)
        for p in projectiles: p.draw(screen)
        
        if game_state == TARGETING:
            mx,my=pygame.mouse.get_pos();tx,ty=mx//TILE_SIZE,my//TILE_SIZE
            if ty<MAP_HEIGHT:s=pygame.Surface((TILE_SIZE,TILE_SIZE),pygame.SRCALPHA);s.fill(C["TARGET"]);screen.blit(s,(tx*TILE_SIZE,ty*TILE_SIZE))

        pygame.draw.rect(screen, C["UI"], (0,SCREEN_HEIGHT-UI_PANEL_HEIGHT,SCREEN_WIDTH,UI_PANEL_HEIGHT))
        pygame.draw.rect(screen, C["BUTTON"], exit_button_rect)
        screen.blit(font.render("Exit",True,C["WHITE"]),font.render("Exit",True,C["WHITE"]).get_rect(center=exit_button_rect.center))
        screen.blit(font.render(f"HP: {player.hp}/{player.max_hp}",True,C["WHITE"]),(20,SCREEN_HEIGHT-55))
        xp_w=150*(player.xp/player.xp_to_next) if player.xp_to_next>0 else 150
        pygame.draw.rect(screen,C["XP_BAR_BG"],(20,SCREEN_HEIGHT-30,150,15)); pygame.draw.rect(screen,C["XP_BAR"],(20,SCREEN_HEIGHT-30,xp_w,15))
        screen.blit(font.render(f"Lvl: {player.level}",True,C["WHITE"]),(200,SCREEN_HEIGHT-55))
        screen.blit(font.render(f"Floor: {floor_number}",True,C["WHITE"]),(200,SCREEN_HEIGHT-30))
        screen.blit(font.render(f"Score: {score}",True,C["WHITE"]),(350,SCREEN_HEIGHT-55))
        screen.blit(font.render(f"High: {high_score}",True,C["WHITE"]),(350,SCREEN_HEIGHT-30))
        for i in range(player.max_inventory):
            rect=inventory_rects[i]; pygame.draw.rect(screen,(0,0,0),rect,2)
            if i<len(player.inventory): screen.blit(player.inventory[i].image,rect.topleft)

        if game_state == GAME_OVER:
            s=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA);s.fill((0,0,0,200));screen.blit(s,(0,0))
            go_text=big_font.render("GAME OVER",True,(255,0,0));screen.blit(go_text,go_text.get_rect(center=(SCREEN_WIDTH/2,SCREEN_HEIGHT/2-50)))
            pygame.draw.rect(screen,C["RESTART_BUTTON"],restart_button_rect)
            restart_text = font.render("RESTART?", True, C["WHITE"])
            screen.blit(restart_text,restart_text.get_rect(center=restart_button_rect.center))

        pygame.display.flip()
        clock.tick(60) # 毎秒60フレームで固定

if __name__ == '__main__':
    main()