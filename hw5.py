import pyglet
import random
import pickle
import atexit
import os
from pybird.game import Game




#具体的fasttrain和eps说明见说明pdf！！！！！！







FAST_TRAIN= True#在这里我写了一个不调用pyglet的加速模式，这样出结果快很多，不然调pyglet会很慢，底层逻辑是一样的，只是固定了dt。
#True开启快速训练，False使用正常调度
TRAIN_MAX_ROUND= 120000#目标训练回合数，从没有Q的情况下我就是用这个训练的
SAVE_EVERY_ROUND= 2000#快速模式下保存周期
SHOW_WINDOW= True
ENABLE_SOUND= False




class Bot:
    def __init__(self, game):
        self.game= game
        # constants
        self.WINDOW_HEIGHT= Game.WINDOW_HEIGHT
        self.PIPE_WIDTH= Game.PIPE_WIDTH
        # this flag is used to make sure at most one tap during
        # every call of run()
        self.tapped= False # 每帧是否已跳
        self.round= 0
        self.game.play()

        # variables for plan
        self.qvalues= {}
        self.lr= 0.5
        self.discount= 0.95
        self.epsilon= 0.001#探索率，可以修改，说明文档中的1.3-1.4w轮是在eps=0.01，4w轮是在epsilon=0.8，无q表的情况下从头开始训练达到的结果
        #现在使用当时的Q表，设定eps为0.001即可，如果要复现从没有Q表达到1000，把dictQ删除，具体看pdf说明
        self.epsilon_min= 0.001#探索率下限
        self.epsilon_decay= 0.9998 #探索率衰减
        self.last_state_key= None
        self.last_action= 0
        self.moves= []
        self.prev_score= 0
        self.high_crash_flag= False
        self.PIPE_GAP= getattr(Game, "PIPE_HEIGHT_INTERVAL", getattr(Game, "PIPE_GAP", 120))

        if os.path.isfile("dict_Q"):
            try:  #读取Q表
                self.qvalues= pickle.load(open("dict_Q", "rb"))
            except Exception:
                self.qvalues= {}  #使用空表

        def do_at_exit():
            pickle.dump(self.qvalues, open("dict_Q", "wb"))
            print("wirte to dict_Q")  # 原注释内容保留

        atexit.register(do_at_exit)

    # this method is auto called every 0.05s by the pyglet
    def run(self):
        if self.game.state == "PLAY":
            self.tapped= False
            # call plan() to execute your plan
            self.plan(self.get_state())
        else: # 游戏结束
            state= self.get_state()#获取当前状态
            bird_state= list(state["bird"])
            bird_state[2]= "dead"
            state["bird"]= bird_state
            # do NOT allow tap
            self.tapped= True
            self.plan(state)
            # restart game
            self.round+= 1
            print("score:", self.game.record.get(), "best: ", self.game.record.best_score, "round: ", self.round)
            if self.epsilon > self.epsilon_min:#若探索率未到下限
                self.epsilon*= self.epsilon_decay
            self.game.restart()
            self.game.play()

    # get the state that robot needed
    def get_state(self):
        state= {}  #初始化状态字典
        # bird's position and status(dead or alive)
        state["bird"]= (int(round(self.game.bird.x)), int(round(self.game.bird.y)), "alive")
        state["pipes"]= []
        # pipes' position
        for i in range(1, len(self.game.pipes), 2): #只取下水管
            p= self.game.pipes[i]
            if p.x < Game.WINDOW_WIDTH:  # this pair of pipes shows on screen；
                x= int(round(p.x))  #水管x坐标
                y= int(round(p.y))  #y坐标
                state["pipes"].append((x, y))#下水管位置
        return state


    # simulate the click action, bird will fly higher when tapped
    # It can be called only once every time slice(every execution cycle of plan())
    def tap(self):
        if not self.tapped:
            self.game.bird.jump()
            self.tapped= True

    def _ensure_state(self, key):
        if key not in self.qvalues:
            self.qvalues[key]= [0.0, 0.0]  #初始化 Q 值

    def _nearest_pipe(self, state):
        bird_x= state["bird"][0]
        pipes= state["pipes"]
        if not pipes:
            return None
        best= None  #当前最佳水管
        best_dx= 1e9
        for px, py in pipes:#遍历水管
            dx= px - bird_x
            if dx >= -self.PIPE_WIDTH and dx < best_dx: #选择最近且在前方或刚过的位置
                best_dx= dx
                best= (px, py)
        if best is None:
            best= min(pipes, key= lambda p: p[0]) #选最靠左的水管
        return best



    def map_state(self, xdif, ydif, vel): #离散化状态空间
        xdif= max(min(xdif, 220), -80)
        ydif= max(min(ydif, 260), -260)
        if xdif < 150:  #近距离更细
            xdif= int(xdif) - (int(xdif) % 10)
        else:  #远距离更粗
            xdif= int(xdif) - (int(xdif) % 50)
        if ydif < 200:  #垂直近处更细
            ydif= int(ydif) - (int(ydif) % 10)
        else:  #垂直远处更粗
            ydif= int(ydif) - (int(ydif) % 40)
        vel_bin= int(round(vel / 20.0))
        return f"{int(xdif)}_{int(ydif)}_{int(vel_bin)}" #返回key



    def select_action(self, key):
        self._ensure_state(key)
        if random.random() < self.epsilon:
            return random.randint(0, 1)
        q0, q1= self.qvalues[key]
        return 0 if q0 >= q1 else 1 #选择更好的动作

    # That's where the robot actually works
    # NOTE Put your code here
    def plan(self, state):
        score= self.game.record.get()
        target= self._nearest_pipe(state)
        if target is None:
            return

        bird_x, bird_y, life= state["bird"]
        px, py= target#目标水管位置
        gap_center= py - self.PIPE_GAP / 2  #水管空隙中心

        dx= px - bird_x#水平差
        dy= bird_y - gap_center#垂直
        vel= self.game.bird.speed #当前速度

        state_key= self.map_state(dx, dy, vel)
        dead= life == "dead"

        passed_pipe= score > self.prev_score
        self.prev_score= score

        if self.last_state_key is not None:
            self.moves.append((self.last_state_key, self.last_action, state_key, passed_pipe))

        if dead:  # 若死亡
            gap_half= self.PIPE_GAP / 2 #半个水管间隙
            self.high_crash_flag= dy > gap_half and self.last_action == 1 #是否上撞且跳跃
            self.update_scores()
            self.last_state_key= None
            self.last_action= 0
            return

        action= self.select_action(state_key)
        if action == 1:
            self.tap()#执行跳跃

        self.last_state_key= state_key
        self.last_action= action

    def update_scores(self):
        history= list(reversed(self.moves))
        t= 1
        for exp in history: #遍历轨迹
            state= exp[0]
            act= exp[1]
            res_state= exp[2]
            passed= exp[3] #是否过管

            if t == 1:  # 第一步死了
                cur_reward= -300
                if self.high_crash_flag and act == 1: #若上撞且跳跃
                    cur_reward+= -700
                next_max= 0.0
            else:  # 非终止状态
                cur_reward= 0.1  #存活奖励
                if passed:
                    cur_reward+= 100  # 过管奖励
                if act == 1:
                    cur_reward+= -0.2  # 拍翅惩罚
                self._ensure_state(res_state) #确保下一个状态存在
                next_max= max(self.qvalues[res_state])

            self._ensure_state(state)
            self.qvalues[state][act]= (#Qlearning更新公式
                (1 - self.lr) * self.qvalues[state][act]
                + self.lr * (cur_reward + self.discount * next_max)  #融合新目标
            )
            t+= 1

        self.moves= []
        self.high_crash_flag= False  # 清除上撞标记
        if FAST_TRAIN and SAVE_EVERY_ROUND > 0 and self.round % SAVE_EVERY_ROUND == 0 and self.round > 0:
            pickle.dump(self.qvalues, open("dict_Q", "wb"))


if __name__ == "__main__":
    show_window= SHOW_WINDOW
    enable_sound= ENABLE_SOUND
    game= Game()
    game.set_sound(enable_sound)
    bot= Bot(game)

    def update(dt):
        game.update(dt)
        bot.run()

    if FAST_TRAIN:#快速训练分支
        dt= Game.TIME_INTERVAL
        while bot.round < TRAIN_MAX_ROUND:
            update(dt)#直接推进游戏
    else: #原始 pyglet主循环结构
        pyglet.clock.schedule_interval(update, Game.TIME_INTERVAL)
        if show_window:
            window= pyglet.window.Window(Game.WINDOW_WIDTH, Game.WINDOW_HEIGHT, vsync= False)

            @window.event
            def on_draw():
                window.clear()
                game.draw()



            pyglet.app.run()#启动事件循环
        else:#不显示窗口
            pyglet.app.run()
