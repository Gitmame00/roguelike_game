import os
import random
import math
from collections import deque

# KivyのConfigを最初にインポートして設定
from kivy.config import Config

# --- ゲーム定数の定義 (Config.set() の前に置く) ---
TILE_SIZE, MAP_WIDTH, MAP_HEIGHT, UI_PANEL_HEIGHT = 48, 25, 15, 60
SCREEN_WIDTH, SCREEN_HEIGHT = TILE_SIZE*MAP_WIDTH, TILE_SIZE*MAP_HEIGHT + UI_PANEL_HEIGHT

Config.set('graphics', 'width', str(SCREEN_WIDTH))
Config.set('graphics', 'height', str(SCREEN_HEIGHT))
Config.set('graphics', 'resizable', '0')
Config.set('graphics', 'fullscreen', '0')
# --- ゲーム定数とConfig設定ここまで ---

# Kivyのインポート
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line
from kivy.core.image import Image as CoreImage

# 色 (Kivyの描画はRGBAの0.0-1.0を使用するため変換が必要)
def get_kivy_color(r, g, b, a=255):
    return (r/255., g/255., b/255., a/255.)

C = {
    "BLACK": get_kivy_color(0,0,0),
    "FLOOR": get_kivy_color(120,90,40),
    "WALL": get_kivy_color(60,40,20),
    "WHITE": get_kivy_color(255,255,255),
    "UI": get_kivy_color(40,40,40),
    "BUTTON": get_kivy_color(180,50,50),
    "HP_BAR": get_kivy_color(0,200,0),
    "HP_BAR_BG": get_kivy_color(80,0,0),
    "XP_BAR": get_kivy_color(0,150,200),
    "XP_BAR_BG": get_kivy_color(0,0,80),
    "TARGET": get_kivy_color(255,0,0,150),
    "RANGE": get_kivy_color(0,100,255,80),
    "RESTART_BUTTON": get_kivy_color(50, 180, 50),
    "PATH_HIGHLIGHT": get_kivy_color(0, 255, 255, 50)
}

# ゲームステート定数
PLAYER_INPUT = "player_input"
PLAYER_MOVING = "player_moving"
ENEMY_TURN = "enemy_turn"
PROJECTILE_ANIMATION = "projectile_animation"
TARGETING = "targeting"
SCREEN_FLASH = "screen_flash"
GAME_OVER = "game_over"
NEW_FLOOR = "new_floor"

# 画像読み込み
base_dir = os.path.dirname(os.path.abspath(__file__))
assets_path = os.path.join(base_dir, 'assets')
kivy_images = {}

# Kivyで画像をロードする関数
def load_kivy_image(path):
    if path not in kivy_images:
        try:
            if not os.path.exists(path):
                print(f"Warning: Image file not found: {path}")
                kivy_images[path] = None
            else:
                kivy_images[path] = CoreImage(path).texture
        except Exception as e:
            print(f"Error loading Kivy image {path}: {e}")
            kivy_images[path] = None
    return kivy_images[path]

# ポッチのアニメーションフレームのパスリスト
pocchi_image_paths = [
    os.path.join(assets_path, 'pocchi_1.png'),
    os.path.join(assets_path, 'pocchi_2.png')
]

# 全ての画像のパスを定義
image_paths_dict = {
    "pocchi": pocchi_image_paths,
    "goblin": os.path.join(assets_path, 'goblin.png'),
    "orc": os.path.join(assets_path, 'orc.png'),
    "golem": os.path.join(assets_path, 'golem.png'),
    "potion": os.path.join(assets_path, 'potion.png'),
    "rock": os.path.join(assets_path, 'rock.png'),
    "holy_grenade": os.path.join(assets_path, 'holy_grenade.png'),
    "bomb": os.path.join(assets_path, 'bomb.png'),
    "rock_projectile": os.path.join(assets_path, 'rock_projectile.png'),
    "stair_image": os.path.join(assets_path, 'stair.png')
}


# 2. クラスの定義
class Entity:
    def __init__(self, x, y, image_path_or_list, hp, name, attack=10):
        self.x, self.y, self.hp, self.max_hp, self.name, self.attack = x, y, hp, hp, name, attack
        self.image_path = image_path_or_list[0] if isinstance(image_path_or_list, list) else image_path_or_list
        self._kivy_texture = None

    def get_kivy_texture(self):
        if self._kivy_texture is None:
            self._kivy_texture = load_kivy_image(self.image_path)
        return self._kivy_texture

    def move(self, dx, dy, dungeon_map, entities):
        new_x, new_y = self.x + dx, self.y + dy
        is_occupied = any(e.x==new_x and e.y==new_y for e in entities if e is not self and not isinstance(e, Boss))
        boss_collision = any(b.x<=new_x<b.x+2 and b.y<=new_y<b.y+2 for b in entities if isinstance(b, Boss))
        if dungeon_map[new_y][new_x] == 0 and not is_occupied and not boss_collision:
            self.x, self.y = new_x, new_y
            return True
        return False

class Player(Entity):
    def __init__(self, x, y, image_paths_dict):
        super().__init__(x, y, image_paths_dict["pocchi"][0], 100, "Player", attack=20)
        self.p_image_paths = image_paths_dict["pocchi"]
        self.current_frame = 0
        self.animation_timer = 0
        self.inventory, self.max_inventory = [], 5
        self.level, self.xp, self.xp_to_next = 1, 0, 100
        self.item_to_throw = None
        self.target_path = []
        self.target_enemy = None

    def update_animation(self):
        self.animation_timer = (self.animation_timer + 1) % 21
        if self.animation_timer == 20: 
            self.current_frame = (self.current_frame + 1) % len(self.p_image_paths)
            self.image_path = self.p_image_paths[self.current_frame]
            self._kivy_texture = None

    def add_xp(self, amount):
        self.xp += amount
        while self.xp >= self.xp_to_next:
            self.level += 1
            self.xp -= self.xp_to_next
            self.xp_to_next = int(self.xp_to_next * 1.5)
            self.max_hp += 20
            self.hp = self.max_hp
            self.attack += 5

class Enemy(Entity):
    def __init__(self, x, y, image_path, hp, name, attack, points):
        super().__init__(x, y, image_path, hp, name, attack); self.points = points
    def take_turn(self, player, dungeon_map, entities, projectiles_list):
        dist = math.hypot(self.x-player.x, self.y-player.y)
        if dist < 8:
            if dist <= 1.5: player.hp -= self.attack
            else: dx=1 if player.x>self.x else -1 if player.x<self.x else 0; dy=1 if player.y>self.y else -1 if player.y<self.y else 0; self.move(dx,dy,dungeon_map,entities)

class RangedEnemy(Enemy):
    def take_turn(self, player, dungeon_map, entities, projectiles_list):
        dist = math.hypot(self.x - player.x, self.y - player.y)
        dx = 1 if player.x > self.x else -1 if player.x < self.x else 0
        dy = 1 if player.y > self.y else -1 if player.y < self.y else 0
        
        is_in_line_of_sight = (self.x == player.x or self.y == player.y)
        
        if is_in_line_of_sight and 1 < dist < 6:
            projectiles_list.append(Projectile(self.x, self.y, player.x, player.y, image_paths_dict["rock_projectile"], self.attack))
        elif dist <= 2:
            self.move(-dx, -dy, dungeon_map, entities)
        elif dist < 8:
            self.move(dx, dy, dungeon_map, entities)

class Projectile:
    def __init__(self, start_x, start_y, target_x, target_y, image_path, damage):
        self.x, self.y = start_x*TILE_SIZE+TILE_SIZE//2, start_y*TILE_SIZE+TILE_SIZE//2
        self.image_path, self.damage = image_path, damage
        angle = math.atan2(target_y-start_y, target_x-start_x)
        self.vx, self.vy = math.cos(angle)*15, math.sin(angle)*15; self.target_pos = (target_x, target_y)
        self._kivy_texture = None

    def get_kivy_texture(self):
        if self._kivy_texture is None:
            self._kivy_texture = load_kivy_image(self.image_path)
        return self._kivy_texture

    def update(self):
        self.x+=self.vx; self.y+=self.vy
        if math.hypot(self.x-(self.target_pos[0]*TILE_SIZE+TILE_SIZE//2), self.y-(self.target_pos[1]*TILE_SIZE+TILE_SIZE//2)) < 20: return True
        return False

class Boss(Enemy):
    def __init__(self, x, y): 
        super().__init__(x, y, image_paths_dict["golem"], 300, "Stone Golem", 30, 1000)
    
    def take_turn(self, player, dungeon_map, entities, projectiles_list=None):
        in_range = (self.x-1<=player.x<self.x+3) and (self.y-1<=player.y<self.y+3)
        if in_range: player.hp-=self.attack
        elif math.hypot((self.x+0.5)-player.x, (self.y+0.5)-player.y) < 8:
            dx=1 if player.x>self.x+0.5 else -1 if player.x<self.x+0.5 else 0; dy=1 if player.y>self.y+0.5 else -1 if player.y<self.y+0.5 else 0; self.move(dx,dy,dungeon_map,entities)
    
    def move(self, dx, dy, dungeon_map, entities):
        nx,ny=self.x+dx,self.y+dy; can_move=True
        for i in range(2):
            for j in range(2):
                if not(0<=ny+j<MAP_HEIGHT and 0<=nx+i<MAP_WIDTH)or dungeon_map[ny+j][nx+i]!=0 or any(e.x==nx+i and e.y==ny+j for e in entities if e is not self): can_move=False; break
            if not can_move: break
        if can_move: self.x, self.y = nx, ny; return True
        return False

class Item:
    def __init__(self,x,y,image_path,name):
        self.x,self.y,self.image_path,self.name=x,y,image_path,name
        self._kivy_texture = None

    def get_kivy_texture(self):
        if self._kivy_texture is None:
            self._kivy_texture = load_kivy_image(self.image_path)
        return self._kivy_texture

class Room:
    def __init__(self,x,y,w,h): self.x1,self.y1,self.x2,self.y2=x,y,x+w,y+h
    def center(self): return ((self.x1+self.x2)//2,(self.y1+self.y2)//2)
    def intersects(self,other): return (self.x1<=other.x2+1 and self.x2>=other.x1-1 and self.y1<=other.y2+1 and self.y2>=other.y1-1)

# パス探索ユーティリティ関数 (BFS)
def find_path(start_x, start_y, target_x, target_y, dungeon_map, obstacles):
    q = deque()
    q.append(((start_x, start_y), []))
    visited = set()
    visited.add((start_x, start_y))

    while q:
        (cx, cy), path = q.popleft()

        if (cx, cy) == (target_x, target_y):
            return path
        
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
            nx, ny = cx + dx, cy + dy

            if not (0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT):
                continue
            
            if dungeon_map[ny][nx] == 1:
                continue
            
            is_occupied = False
            for e in obstacles:
                if isinstance(e, Boss):
                    if e.x <= nx < e.x + 2 and e.y <= ny < e.y + 2:
                        is_occupied = True
                        break
                else:
                    if e.x == nx and e.y == ny:
                        is_occupied = True
                        break
            
            if is_occupied:
                continue

            if (nx, ny) not in visited:
                visited.add((nx, ny))
                q.append(((nx, ny), path + [(nx, ny)]))
    
    return []

def find_path_to_adjacent_of_enemy(start_x, start_y, target_enemy, dungeon_map, player_obj, all_entities):
    obstacles_for_pathfinding = [e for e in all_entities if e is not player_obj and e is not target_enemy] 

    adjacent_empty_tiles = []
    
    if isinstance(target_enemy, Boss):
        for y_offset in range(-1, 3):
            for x_offset in range(-1, 3):
                test_x, test_y = target_enemy.x + x_offset, target_enemy.y + y_offset
                if (0 <= test_x < MAP_WIDTH and 0 <= test_y < MAP_HEIGHT and
                    dungeon_map[test_y][test_x] == 0):
                    if not (target_enemy.x <= test_x < target_enemy.x + 2 and
                            target_enemy.y <= test_y < target_enemy.y + 2):
                        adjacent_empty_tiles.append((test_x, test_y))
    else:
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
            test_x, test_y = target_enemy.x + dx, target_enemy.y + dy
            if (0 <= test_x < MAP_WIDTH and 0 <= test_y < MAP_HEIGHT and
                dungeon_map[test_y][test_x] == 0):
                adjacent_empty_tiles.append((test_x, test_y))
    
    shortest_path = []
    min_len = float('inf')

    for adj_x, adj_y in adjacent_empty_tiles:
        path = find_path(start_x, start_y, adj_x, adj_y, dungeon_map, obstacles_for_pathfinding)
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
            if enemy_type < 0.2 + floor*0.05: entities.append(Enemy(r.center()[0],r.center()[1],image_paths_dict["orc"],int(50*buff),"Orc",int(15*buff),int(100*buff)))
            elif enemy_type < 0.5: entities.append(RangedEnemy(r.center()[0],r.center()[1],image_paths_dict["goblin"],int(25*buff),"Goblin Slinger",int(10*buff),int(60*buff)))
            else: entities.append(Enemy(r.center()[0],r.center()[1],image_paths_dict["goblin"],int(30*buff),"Goblin",int(10*buff),int(50*buff)))
    items=[]
    for r in rooms:
        if random.random()<0.1: items.append(Item(r.center()[0]+1,r.center()[1],image_paths_dict["potion"],"Potion"))
        if random.random()<0.2: items.append(Item(r.center()[0]-1,r.center()[1],image_paths_dict["rock"],"Rock"))
        if random.random()<0.07: items.append(Item(r.center()[0],r.center()[1]+1,image_paths_dict["bomb"],"Bomb"))
        if random.random()<0.05: items.append(Item(r.center()[0],r.center()[1]+1,image_paths_dict["holy_grenade"],"Holy Grenade"))
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
            if enemy_type < 0.3: entities.append(RangedEnemy(ex, ey, image_paths_dict["goblin"], int(25*buff), "Goblin Slinger", int(10*buff), int(60*buff)))
            elif enemy_type < 0.6: entities.append(Enemy(ex,ey,image_paths_dict["orc"],int(50*buff),"Orc",int(15*buff),int(100*buff)))
            else: entities.append(Enemy(ex,ey,image_paths_dict["goblin"],int(30*buff),"Goblin",int(10*buff),int(50*buff)))
    return dungeon_map,player_start,entities,[],stair_pos,False

def load_highscore():
    try:
        with open("highscore.txt","r") as f: return int(f.read())
    except(FileNotFoundError,ValueError): return 0
def save_highscore(score):
    with open("highscore.txt","w") as f: f.write(str(score))

def is_player_adjacent_to_entity(player_obj, entity):
    if isinstance(entity, Boss):
        for bx_offset in range(2):
            for by_offset in range(2):
                if math.hypot(player_obj.x - (entity.x + bx_offset), player_obj.y - (entity.y + by_offset)) <= 1.5:
                    return True
        return False
    else:
        return math.hypot(player_obj.x - entity.x, player_obj.y - entity.y) <= 1.5


# --- マップ描画専用のウィジェットを作成 ---
class MapCanvasWidget(Widget):
    def __init__(self, game_logic_instance, **kwargs):
        super().__init__(**kwargs)
        self.game = game_logic_instance
        self.bind(pos=self.redraw_canvas, size=self.redraw_canvas)

    def redraw_canvas(self, *args):
        self.canvas.clear()
        with self.canvas:
            if not self.game.dungeon_map: # dungeon_mapがまだ空なら描画しない
                return

            # マップ描画
            for y in range(MAP_HEIGHT):
                for x in range(MAP_WIDTH):
                    color_data = C["WALL"] if self.game.dungeon_map[y][x]==1 else C["FLOOR"]
                    Color(*color_data)
                    screen_y = self.y + (MAP_HEIGHT - 1 - y) * TILE_SIZE
                    Rectangle(pos=(self.x + x*TILE_SIZE, screen_y), size=(TILE_SIZE, TILE_SIZE))
            
            # プレイヤーのパスハイライト描画
            if self.game.player.target_path:
                for px, py in self.game.player.target_path:
                    Color(*C["PATH_HIGHLIGHT"])
                    screen_py = self.y + (MAP_HEIGHT - 1 - py) * TILE_SIZE
                    Rectangle(pos=(self.x + px*TILE_SIZE, screen_py), size=(TILE_SIZE, TILE_SIZE))
            
            # 階段描画
            if self.game.stairs_visible:
                stair_texture = load_kivy_image(image_paths_dict["stair_image"])
                stair_screen_y = self.y + (MAP_HEIGHT - 1 - self.game.stair_pos[1]) * TILE_SIZE
                if stair_texture:
                    Color(1,1,1,1)
                    Rectangle(texture=stair_texture, pos=(self.x + self.game.stair_pos[0]*TILE_SIZE, stair_screen_y), size=(TILE_SIZE, TILE_SIZE))
                else:
                    Color(*get_kivy_color(150,0,150))
                    Rectangle(pos=(self.x + self.game.stair_pos[0]*TILE_SIZE, stair_screen_y), size=(TILE_SIZE, TILE_SIZE))

            # アイテム描画
            for item in self.game.items:
                texture = item.get_kivy_texture()
                screen_item_y = self.y + (MAP_HEIGHT - 1 - item.y) * TILE_SIZE
                if texture:
                    Color(1,1,1,1)
                    Rectangle(texture=texture, pos=(self.x + item.x*TILE_SIZE, screen_item_y), size=(TILE_SIZE, TILE_SIZE))

            # 敵描画
            for enemy in self.game.enemies:
                texture = enemy.get_kivy_texture()
                screen_enemy_y = self.y + (MAP_HEIGHT - 1 - enemy.y) * TILE_SIZE
                if texture:
                    Color(1,1,1,1)
                    size = (TILE_SIZE*2, TILE_SIZE*2) if isinstance(enemy, Boss) else (TILE_SIZE, TILE_SIZE)
                    Rectangle(texture=texture, pos=(self.x + enemy.x*TILE_SIZE, screen_enemy_y), size=size)
                # HPバー描画
                hp_bar_pos_y = self.y + (MAP_HEIGHT - 1 - enemy.y) * TILE_SIZE + TILE_SIZE + 5
                hp_bar_w = int(TILE_SIZE * (enemy.hp/enemy.max_hp)) if enemy.max_hp > 0 else 0
                if isinstance(enemy, Boss): hp_bar_w = int(TILE_SIZE * 2 * (enemy.hp/enemy.max_hp))
                Color(*C["HP_BAR_BG"])
                Rectangle(pos=(self.x + enemy.x*TILE_SIZE, hp_bar_pos_y), size=(TILE_SIZE*2 if isinstance(enemy, Boss) else TILE_SIZE, 5))
                Color(*C["HP_BAR"])
                Rectangle(pos=(self.x + enemy.x*TILE_SIZE, hp_bar_pos_y), size=(hp_bar_w, 5))
            
            # プレイヤー描画
            player_texture = self.game.player.get_kivy_texture()
            screen_player_y = self.y + (MAP_HEIGHT - 1 - self.game.player.y) * TILE_SIZE
            if player_texture:
                Color(1,1,1,1)
                Rectangle(texture=player_texture, pos=(self.x + self.game.player.x*TILE_SIZE, screen_player_y), size=(TILE_SIZE, TILE_SIZE))
            # プレイヤーのHPバー描画
            player_hp_bar_pos_y = self.y + (MAP_HEIGHT - 1 - self.game.player.y) * TILE_SIZE + TILE_SIZE + 5
            hp_bar_w_player = int(TILE_SIZE * (self.game.player.hp/self.game.player.max_hp)) if self.game.player.max_hp > 0 else 0
            Color(*C["HP_BAR_BG"])
            Rectangle(pos=(self.x + self.game.player.x*TILE_SIZE, player_hp_bar_pos_y), size=(TILE_SIZE, 5))
            Color(*C["HP_BAR"])
            Rectangle(pos=(self.x + self.game.player.x*TILE_SIZE, player_hp_bar_pos_y), size=(hp_bar_w_player, 5))

            # PLAYER_INPUT状態での移動/攻撃オプションの描画 (パスがない場合のみ)
            if self.game.game_state == PLAYER_INPUT and not self.game.player.target_path:
                for dy in range(-1,2):
                    for dx in range(-1,2):
                        if dx==0 and dy==0: continue
                        tx,ty=self.game.player.x+dx,self.game.player.y+dy
                        if 0<=ty<MAP_HEIGHT and 0<=tx<MAP_WIDTH:
                            screen_ty = self.y + (MAP_HEIGHT - 1 - ty) * TILE_SIZE
                            is_enemy=any(e.x<=tx<e.x+(2 if isinstance(e,Boss)else 1) and e.y<=ty<e.y+(2 if isinstance(e,Boss)else 1) for e in self.game.enemies)
                            
                            if is_enemy: 
                                Color(*get_kivy_color(255,0,0,80))
                                Rectangle(pos=(self.x + tx*TILE_SIZE,screen_ty),size=(TILE_SIZE,TILE_SIZE))
                                Color(*get_kivy_color(255,0,0,255))
                                Line(rectangle=(self.x + tx*TILE_SIZE,screen_ty,TILE_SIZE,TILE_SIZE), width=2)
                            elif self.game.dungeon_map[ty][tx]!=1: 
                                Color(*get_kivy_color(255,255,0,80))
                                Rectangle(pos=(self.x + tx*TILE_SIZE,screen_ty),size=(TILE_SIZE,TILE_SIZE))
                                Color(*get_kivy_color(255,255,0,255))
                                Line(rectangle=(self.x + tx*TILE_SIZE,screen_ty,TILE_SIZE,TILE_SIZE), width=2)

            # 発射物描画
            for p in self.game.projectiles:
                proj_texture = p.get_kivy_texture()
                if proj_texture:
                    Color(1,1,1,1)
                    # p.y はPygame基準のY座標なので、Kivyの描画Y座標に変換する
                    screen_proj_y = self.y + (MAP_HEIGHT * TILE_SIZE) - p.y
                    Rectangle(texture=proj_texture, pos=(self.x + p.x - TILE_SIZE//2, screen_proj_y - TILE_SIZE//2), size=(TILE_SIZE, TILE_SIZE))

            # ターゲティングモードでの範囲表示とターゲット表示
            if self.game.game_state == TARGETING and self.game.last_touch_pos != (0,0):
                for y in range(MAP_HEIGHT):
                    for x in range(MAP_WIDTH):
                        if math.hypot(self.game.player.x-x, self.game.player.y-y)<=4 and self.game.dungeon_map[y][x]==0:
                            Color(*C["RANGE"])
                            screen_range_y = self.y + (MAP_HEIGHT - 1 - y) * TILE_SIZE
                            Rectangle(pos=(self.x + x*TILE_SIZE,screen_range_y),size=(TILE_SIZE,TILE_SIZE))
                
                mx_map_rel, my_map_rel = self.game.last_touch_pos[0] - self.x, self.game.last_touch_pos[1] - self.y
                
                tx_touch = int(mx_map_rel // TILE_SIZE)
                ty_touch = MAP_HEIGHT - 1 - int(my_map_rel // TILE_SIZE)
                
                if 0 <= ty_touch < MAP_HEIGHT and 0 <= tx_touch < MAP_WIDTH:
                    Color(*C["TARGET"])
                    screen_target_y = self.y + (MAP_HEIGHT - 1 - ty_touch) * TILE_SIZE
                    Rectangle(pos=(self.x + tx_touch*TILE_SIZE,screen_target_y),size=(TILE_SIZE,TILE_SIZE))

    def on_touch_down(self, touch):
        if self.collide_point(touch.x, touch.y):
            mx_map_rel, my_map_rel = touch.x - self.x, touch.y - self.y
            
            tile_x = int(mx_map_rel // TILE_SIZE)
            tile_y = MAP_HEIGHT - 1 - int(my_map_rel // TILE_SIZE) # KivyタッチYをゲームロジックYに変換

            print(f"--- Touch Debug ---")
            print(f"Kivy Win Pos: ({touch.x},{touch.y})")
            print(f"Map Widget Pos: ({self.x},{self.y})")
            print(f"Map Local Pos: ({mx_map_rel},{my_map_rel})")
            print(f"Game Tile Pos (Logic): ({tile_x},{tile_y})")
            print(f"Player Pos (Logic): ({self.game.player.x},{self.game.player.y})")

            if not (0 <= tile_x < MAP_WIDTH and 0 <= tile_y < MAP_HEIGHT):
                print(f"Invalid touch: tile ({tile_x},{tile_y}) out of map bounds.")
                return True

            if self.game.game_state == PLAYER_INPUT:
                clicked_enemy = None
                for e in self.game.enemies:
                    if isinstance(e, Boss):
                        if e.x <= tile_x < e.x + 2 and e.y <= tile_y < e.y + 2:
                            clicked_enemy = e
                            break
                    else:
                        if e.x == tile_x and e.y == tile_y:
                            clicked_enemy = e
                            break
                
                if clicked_enemy:
                    if is_player_adjacent_to_entity(self.game.player, clicked_enemy):
                        clicked_enemy.hp -= self.game.player.attack
                        if clicked_enemy.hp <= 0:
                            if isinstance(clicked_enemy, Boss): self.game.bosses_defeated += 1
                            self.game.enemies.remove(clicked_enemy); self.game.score += clicked_enemy.points; self.game.player.add_xp(clicked_enemy.points)
                        self.game.player.target_path = []
                        self.game.player.target_enemy = None
                        self.game.game_state = ENEMY_TURN
                        print("Player directly attacked an adjacent enemy. Enemy turn.")
                    else:
                        all_entities_in_scope = [self.game.player] + self.game.enemies
                        path_to_adj = find_path_to_adjacent_of_enemy(self.game.player.x, self.game.player.y, clicked_enemy, self.game.dungeon_map, self.game.player, all_entities_in_scope)
                        if path_to_adj:
                            self.game.player.target_path = path_to_adj
                            self.game.player.target_enemy = clicked_enemy
                            self.game.game_state = PLAYER_MOVING
                            print(f"Player set path to attack {clicked_enemy.name}. Player moving.")
                        else:
                            self.game.player.target_path = []; self.game.player.target_enemy = None
                            print("No path found to adjacent enemy.")
                elif self.game.dungeon_map[tile_y][tile_x] == 0:
                    all_entities_in_scope = [self.game.player] + self.game.enemies
                    path = find_path(self.game.player.x, self.game.player.y, tile_x, tile_y, self.game.dungeon_map, [e for e in all_entities_in_scope if e is not self.game.player])
                    if path:
                        self.game.player.target_path = path
                        self.game.player.target_enemy = None
                        self.game.game_state = PLAYER_MOVING
                        print(f"Player set path to {tile_x},{tile_y}. Player moving.")
                    else:
                        self.game.player.target_path = []; self.game.player.target_enemy = None
                        print("No path found to target tile.")
                elif (tile_x, tile_y) == (self.game.player.x, self.game.player.y):
                    self.game.player.target_path = []; self.game.player.target_enemy = None
                    print("Player clicked on self. Path cleared.")

            elif self.game.game_state == TARGETING:
                tile_x_logic = tile_x
                tile_y_logic = tile_y
                
                if not (0 <= tile_x_logic < MAP_WIDTH and 0 <= tile_y_logic < MAP_HEIGHT):
                    self.game.game_state = PLAYER_INPUT
                    self.game.player.item_to_throw = None
                    print("Targeting cancelled: out of map bounds.")
                    self.game.last_touch_pos = (0,0)
                    return True

                item = self.game.player.inventory[self.game.player.item_to_throw]
                target_entity = None
                for e in self.game.enemies:
                    if isinstance(e, Boss):
                        if e.x <= tile_x_logic < e.x + 2 and e.y <= tile_y_logic < e.y + 2:
                            target_entity = e
                            break
                    else:
                        if e.x == tile_x_logic and e.y == tile_y_logic:
                            target_entity = e
                            break
                
                if target_entity and math.hypot(self.game.player.x-tile_x_logic, self.game.player.y-tile_y_logic) <= 4:
                    damage = 9999 if item.name == "Holy Grenade" else 30
                    target_entity.hp -= damage
                    if target_entity.hp <= 0:
                        if isinstance(target_entity, Boss): self.game.bosses_defeated += 1
                        self.game.enemies.remove(target_entity); self.game.score += target_entity.points; self.game.player.add_xp(target_entity.points)
                    self.game.player.inventory.pop(self.game.player.item_to_throw); 
                    self.game.player.item_to_throw = None
                    self.game.game_state = ENEMY_TURN
                    print(f"Player used {item.name} on {target_entity.name}. Enemy turn.")
                else: 
                    self.game.game_state = PLAYER_INPUT
                    self.game.player.item_to_throw = None
                    print("Targeting cancelled: invalid target or out of range.")
                self.game.last_touch_pos = (0,0)
            
            self.game.last_touch_pos = touch.pos
            return True
        return super().on_touch_down(touch)

# --- GameScreenクラス (FloatLayoutを継承し、マップとUIを子ウィジェットとして持つ) ---
class GameScreen(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # --- デバッグ用: 背景色を設定 ---
        with self.canvas.before:
            Color(1, 0, 0, 0.5) # 半透明の赤
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)
        
        def update_bg_rect(instance, value):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size
        self.bind(pos=update_bg_rect, size=update_bg_rect)
        # --- デバッグ用ここまで ---
        
        self.game_state = NEW_FLOOR
        self.floor_number = 0
        self.score = 0
        self.bosses_defeated = 0
        self.high_score = 0
        
        self.player = Player(0, 0, image_paths_dict)
        self.enemies = []
        self.items = []
        self.dungeon_map = []
        self.stair_pos = (0,0)
        self.stairs_visible = False
        self.projectiles = []
        self.flash_timer = 0
        self.last_touch_pos = (0,0)

        # --- マップ描画ウィジェット ---
        self.map_widget = MapCanvasWidget(self)
        self.map_widget.size_hint = (1, None)
        self.map_widget.height = SCREEN_HEIGHT - UI_PANEL_HEIGHT
        self.map_widget.pos_hint = {'x': 0, 'y': UI_PANEL_HEIGHT / SCREEN_HEIGHT}
        self.add_widget(self.map_widget)

        # --- UIパネルの構築 ---
        self.ui_panel = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=UI_PANEL_HEIGHT,
            pos_hint={'x': 0, 'y': 0}
        )
        # HP/XP表示とレベル
        stats_layout = BoxLayout(orientation='vertical', size_hint_x=0.3)
        self.hp_label = Label(text=f"HP: {self.player.hp}/{self.player.max_hp}", size_hint_y=0.5, color=C["WHITE"], font_size='18sp')
        self.hp_bar = ProgressBar(max=self.player.max_hp, value=self.player.hp, size_hint_y=0.5)
        stats_layout.add_widget(self.hp_label)
        stats_layout.add_widget(self.hp_bar)
        self.ui_panel.add_widget(stats_layout)

        xp_level_layout = BoxLayout(orientation='vertical', size_hint_x=0.3)
        self.level_label = Label(text=f"Lvl: {self.player.level}", size_hint_y=0.5, color=C["WHITE"], font_size='18sp')
        self.xp_bar = ProgressBar(max=self.player.xp_to_next, value=self.player.xp, size_hint_y=0.5)
        xp_level_layout.add_widget(self.level_label)
        xp_level_layout.add_widget(self.xp_bar)
        self.ui_panel.add_widget(xp_level_layout)

        # スコア表示
        score_layout = BoxLayout(orientation='vertical', size_hint_x=0.2)
        self.score_label = Label(text=f"Score: {self.score}", size_hint_y=0.5, color=C["WHITE"], font_size='18sp')
        self.highscore_label = Label(text=f"High: {self.high_score}", size_hint_y=0.5, color=C["WHITE"], font_size='18sp')
        score_layout.add_widget(self.score_label)
        score_layout.add_widget(self.highscore_label)
        self.ui_panel.add_widget(score_layout)

# インベントリ
        self.inventory_layout = GridLayout(cols=self.player.max_inventory, size_hint_x=0.5, padding=5, spacing=5)
        self.inventory_slots = []
        for i in range(self.player.max_inventory):
            # --- 修正箇所: スロットの構造を変更 ---
            # 各スロットをFloatLayoutにする
            slot_layout = FloatLayout()
            
            # アイテム画像用のImageウィジェット
            slot_image = Image(source='', size_hint=(1, 1), pos_hint={'center_x': 0.5, 'center_y': 0.5})
            
            # タップイベント用の透明なButtonウィジェット
            slot_button = Button(
                background_color=(0,0,0,0), # 透明
                background_normal='',
                size_hint=(1, 1),
                pos_hint={'x': 0, 'y': 0}
            )
            slot_button.bind(on_press=self.on_inventory_slot_press)
            slot_button.item_index = i
            
            slot_layout.add_widget(slot_image)
            slot_layout.add_widget(slot_button)
            
            # imageウィジェットへの参照を保存しておく
            self.inventory_slots.append({'layout': slot_layout, 'image': slot_image})
            self.inventory_layout.add_widget(slot_layout)
            # --- 修正箇所ここまで ---
        self.ui_panel.add_widget(self.inventory_layout)

        # Exitボタン
        self.exit_button = Button(text="Exit", size_hint_x=0.2, background_normal='', background_color=C["BUTTON"][:3] + (1,), color=C["WHITE"], font_size='18sp')
        self.exit_button.bind(on_press=self.on_exit_button_press)
        self.ui_panel.add_widget(self.exit_button)
        # --- UIパネルの構築ここまで ---
        self.add_widget(self.ui_panel)

# --- GAME OVER画面のウィジェットを作成 ---
        # --- 修正箇所: size_hint=(1, 1), pos_hint={'x':0, 'y':0} を追加 ---
        self.game_over_layout = FloatLayout(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        
        # 背景のRectangleを作成し、レイアウトのサイズと位置に追従させる
        with self.game_over_layout.canvas.before:
            Color(0,0,0,0.7)
            self.game_over_bg = Rectangle(pos=self.pos, size=self.size)

        def update_bg_rect(instance, value):
            self.game_over_bg.pos = instance.pos
            self.game_over_bg.size = instance.size
        
        self.game_over_layout.bind(pos=update_bg_rect, size=update_bg_rect)
        # --- 修正箇所ここまで ---
        
        self.game_over_label = Label(
            text="GAME OVER",
            font_size='74sp',
            color=(1,0,0,1),
            size_hint=(None, None),
            size=(400,100),
            pos_hint={'center_x': 0.5, 'center_y': 0.6}
        )
        self.game_over_layout.add_widget(self.game_over_label)
        
        self.restart_button = Button(
            text="RESTART?",
            font_size='24sp',
            size_hint=(None, None),
            size=(200,50),
            pos_hint={'center_x': 0.5, 'center_y': 0.4},
            background_normal='',
            background_color=C["RESTART_BUTTON"]
        )
        self.restart_button.bind(on_press=self.on_restart_button_press)
        self.game_over_layout.add_widget(self.restart_button)
        # --- GAME OVER画面のウィジェットここまで ---

        Clock.schedule_interval(self.update, 1.0 / 60.0)

        # setup_game() は NEW_FLOOR ステートで呼ばれる

    def setup_game(self):
        self.floor_number += 1
        self.dungeon_map, start_pos, self.enemies, self.items, self.stair_pos, self.stairs_visible = \
            generate_dungeon(MAP_WIDTH, MAP_HEIGHT, self.floor_number, self.bosses_defeated)
        
        self.player.x, self.player.y = start_pos
        self.player.target_path = []
        self.player.target_enemy = None
        self.player.hp = self.player.max_hp
        
        self.load_high_score()
        print(f"Game setup for Floor {self.floor_number}. Player at {self.player.x}, {self.player.y}")
        self.game_state = PLAYER_INPUT
        self.update_ui()

    def load_high_score(self):
        self.high_score = load_highscore()

    def update(self, dt):
        if self.game_state == NEW_FLOOR:
            self.setup_game()
            return
            
        if self.player.hp <= 0:
            if self.game_state != GAME_OVER:
                self.game_state = GAME_OVER
                if self.score > self.high_score: 
                    save_highscore(self.score)
                    self.high_score = self.score
                print("GAME OVER")
                if not self.game_over_layout.parent:
                    self.add_widget(self.game_over_layout)
            self.update_ui()
            return

        self.player.update_animation()
        self.map_widget.redraw_canvas()

        all_entities = [self.player] + self.enemies

        if self.game_state == PLAYER_MOVING:
            if self.player.target_path:
                next_x, next_y = self.player.target_path[0]
                
                enemy_at_next_step = None
                for e in self.enemies:
                    if isinstance(e, Boss):
                        if e.x <= next_x < e.x + 2 and e.y <= next_y < e.y + 2:
                            enemy_at_next_step = e
                            break
                    else:
                        if e.x == next_x and e.y == next_y:
                            enemy_at_next_step = e
                            break

                if enemy_at_next_step:
                    enemy_at_next_step.hp -= self.player.attack
                    if enemy_at_next_step.hp <= 0:
                        if isinstance(enemy_at_next_step, Boss): self.bosses_defeated += 1
                        self.enemies.remove(enemy_at_next_step); self.score += enemy_at_next_step.points; self.player.add_xp(enemy_at_next_step.points)
                    self.player.target_path = []
                    self.player.target_enemy = None
                    self.game_state = ENEMY_TURN
                    print("Player attacked an enemy and turn ended.")
                else:
                    self.player.x, self.player.y = next_x, next_y
                    self.player.target_path.pop(0)

                    item_to_pick = next((i for i in self.items if i.x==self.player.x and i.y==self.player.y), None)
                    if item_to_pick and len(self.player.inventory)<self.player.max_inventory: 
                        self.player.inventory.append(item_to_pick); self.items.remove(item_to_pick)

                    if self.player.x==self.stair_pos[0] and self.player.y==self.stair_pos[1] and self.stairs_visible: 
                        self.game_state = NEW_FLOOR
                        print("Player reached stairs. New floor!")
                    else: 
                        self.game_state = ENEMY_TURN
                        print("Player moved one step. Enemy turn.")
            else:
                if self.player.target_enemy and self.player.target_enemy in self.enemies and \
                   is_player_adjacent_to_entity(self.player, self.player.target_enemy):
                    self.player.target_enemy.hp -= self.player.attack
                    if self.player.target_enemy.hp <= 0:
                        if isinstance(self.player.target_enemy, Boss): self.bosses_defeated += 1
                        self.enemies.remove(self.player.target_enemy); self.score += self.player.target_enemy.points; self.player.add_xp(self.player.target_enemy.points)
                self.player.target_enemy = None
                self.game_state = PLAYER_INPUT
                print("Player path completed. Awaiting new input.")

        elif self.game_state == SCREEN_FLASH:
            self.game_state = ENEMY_TURN 

        elif self.game_state == ENEMY_TURN:
            self.projectiles = []
            for enemy in self.enemies:
                if isinstance(enemy, RangedEnemy): enemy.take_turn(self.player, self.dungeon_map, all_entities, self.projectiles)
                else: enemy.take_turn(self.player, self.dungeon_map, all_entities, self.projectiles)
            
            if not self.projectiles:
                if not self.stairs_visible and not self.enemies: self.stairs_visible = True
                
                if self.player.target_path:
                    self.game_state = PLAYER_MOVING
                    print("Enemy turn finished. Player continues moving.")
                else:
                    self.game_state = PLAYER_INPUT
                    print("Enemy turn finished. Awaiting player input.")
            else: 
                self.game_state = PROJECTILE_ANIMATION
                print("Enemy turn finished. Projectiles in air.")

        elif self.game_state == PROJECTILE_ANIMATION:
            projectiles_to_remove = []
            for p in self.projectiles:
                if p.update():
                    player_center_x = self.player.x * TILE_SIZE + TILE_SIZE // 2
                    player_center_y = self.player.y * TILE_SIZE + TILE_SIZE // 2

                    if math.hypot(p.x - player_center_x, p.y - player_center_y) < TILE_SIZE / 2:
                        self.player.hp -= p.damage
                        print(f"Player hit by projectile! HP: {self.player.hp}")
                    projectiles_to_remove.append(p)
            for p in projectiles_to_remove:
                self.projectiles.remove(p)

            if not self.projectiles:
                if not self.stairs_visible and not self.enemies: self.stairs_visible = True
                
                if self.player.target_path:
                    self.game_state = PLAYER_MOVING
                    print("Projectile animation finished. Player continues moving.")
                else:
                    self.game_state = PLAYER_INPUT
                    print("Projectile animation finished. Awaiting player input.")
        self.update_ui()


    def on_exit_button_press(self, instance):
        App.get_running_app().stop()

    def on_restart_button_press(self, instance):
        if self.game_over_layout.parent:
            self.remove_widget(self.game_over_layout)
        
        self.game_state = NEW_FLOOR
        self.floor_number = 0
        self.score = 0
        self.bosses_defeated = 0
        self.player = Player(0, 0, image_paths_dict)
        # --- 追加: 発射物リストをクリア ---
        self.projectiles = []
        # --- 追加ここまで ---

    def on_inventory_slot_press(self, instance):
        item_index = instance.item_index
        if item_index < len(self.player.inventory):
            item = self.player.inventory[item_index]
            print(f"Inventory slot {item_index} pressed: {item.name}")
            if self.game_state == PLAYER_INPUT:
                if item.name == "Potion":
                    if self.player.hp < self.player.max_hp: 
                        self.player.hp = min(self.player.max_hp, self.player.hp + 40)
                        self.player.inventory.pop(item_index)
                        self.game_state = ENEMY_TURN
                        print("Used Potion. Enemy turn.")
                elif item.name in ["Rock", "Holy Grenade"]:
                    self.game_state = TARGETING
                    self.player.item_to_throw = item_index
                    print(f"Targeting mode activated for {item.name}.")
                elif item.name == "Bomb":
                    for e in self.enemies: e.hp -= 20
                    self.enemies = [e for e in self.enemies if e.hp > 0]
                    self.player.inventory.pop(item_index)
                    self.game_state = ENEMY_TURN
                    print("Used Bomb. Enemy turn.")
        else:
            print(f"Inventory slot {item_index} pressed: empty.")

    def update_ui(self):
        self.hp_label.text = f"HP: {self.player.hp}/{self.player.max_hp}"
        self.hp_bar.max = self.player.max_hp
        self.hp_bar.value = self.player.hp

        self.level_label.text = f"Lvl: {self.player.level}"
        self.xp_bar.max = self.player.xp_to_next
        self.xp_bar.value = self.player.xp

        self.score_label.text = f"Score: {self.score}"
        self.highscore_label.text = f"High: {self.high_score}"

        # インベントリの表示更新
        for i, slot_data in enumerate(self.inventory_slots):
            slot_image_widget = slot_data['image']
            if i < len(self.player.inventory):
                item = self.player.inventory[i]
                
                # sourceがまだ設定されていないか、変更が必要な場合のみ更新
                if slot_image_widget.source != item.image_path:
                    slot_image_widget.source = item.image_path
            else:
                # sourceが空でない場合のみ更新
                if slot_image_widget.source != '':
                    slot_image_widget.source = ''
        


        
class RogueLikeApp(App):
    def build(self):
        self.game_screen = GameScreen()
        return self.game_screen

if __name__ == '__main__':
    RogueLikeApp().run()