from Agent import Agent
from collections import deque,defaultdict

class MyAI(Agent):

    def __init__(self):
        # ======================================================================
        # YOUR CODE BEGINS
        # ======================================================================

        self.W= 10
        self.H= 10
        self.start= (0,0)
        self.goal= (self.W-1,self.H-1)
        self.visited= set()#记录哪里安全
        self.safe= set([self.start])
        self.que_pits=set()#确定有坑的地方
        self.que_wumpus= set()#确定有怪的地方
        self.dead_wumpus=set()#死了的怪


        self.breeze_at= {}#记一下某格有无风
        self.stench_at= {}#有无臭味


        self.action_queue= []
        self.arrows_left=3#三支箭
        self.has_gold= False
        self.pending_enter_after_shoot=None#射完箭之后打算进去的那个格子


#策略上的一些设置
        self.MAX_EXTRA=25 #拿到金子后不急着走，最多再多逛25步，以防有的问题
        self.MAX_GUESS_LIMIT=30#好像没什么时间限制作业要求，那就嗯举

        self.prev_pos = None #上一回合所在位置，用于检测震荡！！！！！！！！！！！！

        self.stuck = 0#连续被迫回头的计数，检测震荡用

        self.PIT_THRESHOLD_BASE = 0.06#基线容忍坑概率
        self.PIT_THRESHOLD_STEP = 0.06#每次被迫回头时阈值递增步长
        self.PIT_THRESHOLD_MAX = 0.30



    def in_bounds(self,x,y):#有没有走出地图边界
        return 0<=x<self.W and 0<=y<self.H

    def neighbors(self,x,y):
        for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
            nx,ny= x+dx,y+dy
            if self.in_bounds(nx,ny):
                yield (nx,ny)

    def to_action(self,frm,to):#计算从A格走到相邻B格需要哪个动作
        fx,fy= frm
        tx,ty= to
        dx,dy= tx-fx,ty-fy
        if dx==-1 and dy==0:
            return Agent.Action.LEFT
        if dx==1 and dy==0:
            return Agent.Action.RIGHT
        if dx==0 and dy==1:
            return Agent.Action.FORWARD
        if dx==0 and dy==-1:
            return Agent.Action.BACKWARD
        #这个情况应该不会发生，随便返回个GRAB占位
        return Agent.Action.GRAB


    def bfs_path(self,start,target,passable):#用BFS找最短路，只走安全的
        if start==target:
            return [start]
        q= deque([start])
        prev= {start:None}
        while q:
            cur= q.popleft()
            for nx,ny in self.neighbors(*cur):
                np= (nx,ny)
                if np in prev:
                    continue
                if np not in passable:
                    continue
                prev[np]= cur
                if np==target:#找到路了 倒推回去
                    path= [np]
                    while path[-1]!=start:
                        path.append(prev[path[-1]])
                    path.reverse()
                    return path
                q.append(np)
        return None

    def plan_to(self,cur,target):#规划一连串动作去目标点
        path= self.bfs_path(cur,target,self.safe|set([cur]))
        if not path or len(path)<2:
            return []
        actions= []
        for i in range(1,len(path)):
            actions.append(self.to_action(path[i-1],path[i]))
        return actions


    def add_safe_neighbors_if_no_hints(self,x,y,has_stench,has_breeze):#如果没风也没臭味，那周围四个格子无事
        if (not has_breeze) and (not has_stench):
            for n in self.neighbors(x,y):
                if n not in self.que_pits and n not in self.que_wumpus:
                    self.safe.add(n)

    def infer_simple_logic(self):#一个循环检查：看看有没有就剩这一个可能性的情况，对坑
        changed= True
        while changed:
            changed= False
            for (cx,cy),bz in list(self.breeze_at.items()):
                if not bz:
                    continue#如果周围已经确认有坑了，那就不用推断了
                if any((nx,ny) in self.que_pits for (nx,ny) in self.neighbors(cx,cy)):
                    continue
                candidates= []
                for nx,ny in self.neighbors(cx,cy):
                    p= (nx,ny)
                    if p in self.safe:
                        continue
                    if p in self.que_wumpus or p in self.dead_wumpus:
                        continue
                    if p in self.que_pits:
                        continue
                    candidates.append(p)
                if len(candidates)==1:
                    p= candidates[0]
                    if p not in self.que_pits:
                        self.que_pits.add(p)
                        self.safe.discard(p)
                        changed= True

            for (cx,cy),st in list(self.stench_at.items()):#怪兽，逻辑跟上面一样
                if not st:
                    continue
                if any((nx,ny) in self.que_wumpus for (nx,ny) in self.neighbors(cx,cy)):
                    continue
                candidates=[]
                for nx,ny in self.neighbors(cx,cy):
                    p= (nx,ny)
                    if p in self.safe:
                        continue
                    if p in self.que_pits:
                        continue
                    if p in self.que_wumpus or p in self.dead_wumpus:
                        continue
                    candidates.append(p)
                if len(candidates)==1:
                    p= candidates[0]
                    if p not in self.que_wumpus:
                        self.que_wumpus.add(p)
                        self.safe.discard(p)
                        changed= True




    def frontier_unknown(self):#找边缘那些还没探索的格子，去过的地方所有的邻居-已知的安全-已知的坑/怪-去过的格子
        front= set()
        for (x,y) in self.visited:
            for n in self.neighbors(x,y):
                if n in self.safe:
                    continue
                if n in self.que_pits:
                    continue
                if n in self.que_wumpus:
                    continue
                if n in self.dead_wumpus:
                    continue
                if n not in self.visited:
                    front.add(n)
        return front


    def update_knowledge(self,pos,stench,breeze,scream):#每次一栋后更新位置信息
        x,y= pos
        self.visited.add(pos)
        self.safe.add(pos)

        if scream:#惨叫，怪兽死了
            if pos in self.que_wumpus:
                self.que_wumpus.discard(pos)
            self.dead_wumpus.add(pos)
            self.safe.add(pos)
        self.stench_at[pos]= bool(stench)
        self.breeze_at[pos]= bool(breeze)
        self.add_safe_neighbors_if_no_hints(x,y,bool(stench),bool(breeze))

        self.infer_simple_logic()#多跑几遍循环，看看能不能推断出那种显而易见的坑



    def get_border_info(self,frontier):#理一下所有frontier的关系，去过的地方所有的邻居-已知的安全-已知的坑/怪-去过的格子
        vars_list=list(frontier)
        idx= {v:i for i,v in enumerate(vars_list)}

        possible_vals= [set([0,1,2]) for _ in vars_list]#0没东西 1坑 2怪


        for (cx,cy),bz in self.breeze_at.items():
            if not bz:
                for n in self.neighbors(cx,cy):
                    if n in idx:
                        possible_vals[idx[n]].discard(1)
        for (cx,cy),st in self.stench_at.items():
            if not st:
                for n in self.neighbors(cx,cy):
                    if n in idx:
                        possible_vals[idx[n]].discard(2)

        for p in self.que_pits:#已经确定是坑或怪的，直接固定死
            if p in idx:
                possible_vals[idx[p]]= set([1])
        for w in self.que_wumpus:
            if w in idx:
                possible_vals[idx[w]]=set([2])
        for s in (self.safe|self.dead_wumpus):
            if s in idx:
                possible_vals[idx[s]]=set([0])

        breeze_true=[]#记录哪些地方大概率有坑
        for (cx,cy),bz in self.breeze_at.items():
            if not bz:
                continue
            if any((nx,ny) in self.que_pits for (nx,ny) in self.neighbors(cx,cy)):#风是已知的坑吹过来的，不管了
                continue
            S= [idx[n] for n in self.neighbors(cx,cy) if n in idx]#未知的坑，周围一圈加入breezetrue
            if S:
                breeze_true.append(S)

        stench_true=[]#大概率有怪
        for (cx,cy),st in self.stench_at.items():
            if not st:
                continue
            if (cx,cy) in self.dead_wumpus:
                continue
            if any(((nx,ny) in self.que_wumpus) or ((nx,ny) in self.dead_wumpus) for (nx,ny) in self.neighbors(cx,cy)):
                continue
            S= [idx[n] for n in self.neighbors(cx,cy) if n in idx]
            if S:
                stench_true.append(S)

        return vars_list,idx,possible_vals,breeze_true,stench_true


    def guess_risk_byBFs(self):#对边缘所有未知格子bfs穷举是坑还是怪的所有可能性。只有当某种可能性符合现在的风和臭味时，才算数。
        frontier= self.frontier_unknown()
        if not frontier:
            return 0,{},{},{}

        vars_list,idx,possible_vals,breeze_true,stench_true= self.get_border_info(frontier)
        n= len(vars_list)
        if n==0:
            return 0,{},{},{}


        if n>self.MAX_GUESS_LIMIT: #变量过多（此处30）放弃枚举，返回useful_count作为启发/平局优先级
            useful_count= {vars_list[i]:0 for i in range(n)}
            for S in breeze_true:
                for vi in S:
                    useful_count[vars_list[vi]]+= 1
            for S in stench_true:
                for vi in S:
                    useful_count[vars_list[vi]]+= 1
            return 0,{},{},useful_count

        P_left= max(0,3-len(self.que_pits))#剩余的坑，不考虑已得到
        W_left= max(0,3-(len(self.que_wumpus)+len(self.dead_wumpus)))#同上，剩余的怪


        appear= [0]*n#统计每个未知格子牵扯了多少条规则，如果一个格子旁既有风又臭，那关键点
        for S in breeze_true:
            for vi in S:
                appear[vi]+= 1
        for S in stench_true:
            for vi in S:
                appear[vi]+= 1


        order= sorted(range(n),key=lambda i:(len(possible_vals[i]),-appear[i]))
        #len(poss)MRV，先猜那些没得选的（比如只能是怪的），这样能最快填满；appear先猜那些牵扯规则最多的，这样能最快触发剪枝

        assignment= [-1]*n  #-1未定,0空,1坑, 2怪
        usedP= 0#用了几个坑（不能超3个）
        usedW= 0#用了几个怪
        total= 0#多少种合法的填法
        pit_counts= [0]*n#如果是合法的，第i个格子是坑的情况出现了几次
        wum_counts= [0]*n#是怪的情况出现了几次

        def check_guess_valid():#看看已填的坑or怪是否已经违背了规则
            for S in breeze_true:
                ok=False#规则满足了吗（是不是已经填了个坑
                und=False#是不是有格子没填
                for vi in S:
                    v= assignment[vi]
                    if v==1:
                        ok= True
                        break
                    if v==-1 and 1 in possible_vals[vi]:
                        und=True#未来有机会变成坑，先不判死刑
                if not ok and not und:
                    return False#剪枝

            for S in stench_true:#同上
                ok= False
                und= False
                for vi in S:
                    v= assignment[vi]
                    if v==2:
                        ok= True
                        break
                    if v==-1 and 2 in possible_vals[vi]:
                        und= True
                if not ok and not und:
                    return False
            return True

        def check_final_rules():#递归到底了，检查是不是所有的风or臭都找到了源头
            for S in breeze_true:
                if not any(assignment[vi]==1 for vi in S):
                    return False
            for S in stench_true:
                if not any(assignment[vi]==2 for vi in S):
                    return False
            return True




        def dfs(k):
            nonlocal usedP,usedW,total
            if k==n:
                if check_final_rules():
                    total+= 1
                    for i in range(n):
                        v= assignment[i]
                        if v==1:
                            pit_counts[i]+= 1
                        elif v==2:
                            wum_counts[i]+= 1
                return

            vi= order[k]#0优先，因为通常不占用坑or怪的数量额，更容易通过约束
            for val in (0,1,2):
                if val not in possible_vals[vi]:
                    continue
                if val==1 and usedP+1>P_left:
                    continue
                if val==2 and usedW+1>W_left:
                    continue

                prevP,prevW= usedP,usedW
                if val==1:
                    usedP+= 1
                if val==2:
                    usedW+= 1
                assignment[vi]= val
                if check_guess_valid():
                    dfs(k+1)#如果通顺，继续k+1


                assignment[vi]=-1
                usedP,usedW= prevP,prevW#回溯

        dfs(0)

        pit_cnt= {vars_list[i]:pit_counts[i] for i in range(n)}
        wum_cnt= {vars_list[i]:wum_counts[i] for i in range(n)}
        useful_count= {vars_list[i]:appear[i] for i in range(n)}
        return total,pit_cnt,wum_cnt,useful_count






    def should_exit_now(self, cur):#出口不安全，现在不撤
        if self.goal not in self.safe:
            return False

        if self.has_gold:#如果拿到了金子，优先去撤
            return True


        unvisited_safe = [p for p in self.safe if p not in self.visited]
        frontier = self.frontier_unknown()
        if cur == self.goal and not unvisited_safe and not frontier:
            return True#在终点，没有可探索的安全格，也推不出新信息时撤


        to_goal = self.bfs_path(cur, self.goal, self.safe | set([cur]))
        if not to_goal:
            return False
        direct_cost = len(to_goal) - 1

        extra = 0#看看如果再去贪最近的一个安全格子，会多走几步
        if unvisited_safe:
            best_path = None
            best = None
            for p in unvisited_safe:
                path = self.bfs_path(cur, p, self.safe | set([cur]))
                if path and (best_path is None or len(path) < len(best_path)):
                    best_path = path
                    best = p
            if best_path:
                to_p = len(best_path) - 1
                back_to_goal = self.bfs_path(best, self.goal, self.safe | set([best]))
                back_cost = len(back_to_goal) - 1 if back_to_goal else direct_cost
                extra = max(0, to_p + back_cost - direct_cost)

        if extra > self.MAX_EXTRA:#多走太多 不值 撤
            return True

        if cur == self.goal and not unvisited_safe:#在终点 没有未访问的安全 撤
            return True

        return False



    def decide_probe_action(self, cur, pit_threshold):#敢死队模式
        #一般只走安全的路即0%概率死的路。但如果被风和臭味包围无路可退，或卡住太久，必须冒险迈出一步，此函数用于计算这个迈出这步的概率
        total, pit_cnt, wum_cnt, useful_count = self.guess_risk_byBFs()

        candidates = []
        for n in self.neighbors(*cur):
            if (n in self.safe) or (n in self.que_pits) or (n in self.que_wumpus) or (n in self.dead_wumpus):
                continue#跳过
            candidates.append(n)#只选bfs后得到的未知的、可能是坑也可能不是的格子
        if not candidates:
            return None

        if total>0:
            scored= []
            for n in candidates:
                pc=pit_cnt.get(n,0)
                wc =wum_cnt.get(n, 0)
                pit_prob=pc/ float(total)#是坑的概率


                scored.append((#元组排序
                    pit_prob,
                    -useful_count.get(n, 0),#线索价值（越大越好 所以加-
                    abs(n[0] - self.goal[0]) + abs(n[1] - self.goal[1]),#离家距离越近越好
                    wc,
                    n
                ))


            scored.sort()
            pit_prob, _, _, wc, target = scored[0]


            if pit_prob <= pit_threshold:
                if wc > 0 and self.arrows_left > 0:#是怪吗，是的话射
                    return [Agent.Action.SHOOT, self.to_action(cur, target)]
                return [self.to_action(cur, target)]



        #当total==0或最优候选超阈值时 使用本地启发式推进一步
        fallback=[]
        for n in candidates:
            breeze_touch = sum(1 for m in self.neighbors(*n) if self.breeze_at.get(m, False))#邻接已知有风的格，越多越危险
            stench_touch = sum(1 for m in self.neighbors(*n) if self.stench_at.get(m, False))#邻接多少个有臭格

            dist_goal = abs(n[0] - self.goal[0]) + abs(n[1] - self.goal[1])#越近越好
            fallback.append((breeze_touch, stench_touch, dist_goal, n))
        fallback.sort()
        _, _, _, target2 = fallback[0]

        if self.arrows_left > 0 and any(self.stench_at.get(m, False) for m in self.neighbors(*target2)):#若目标邻接臭且有箭，没辙了试一下
            return [Agent.Action.SHOOT, self.to_action(cur, target2)]
        return [self.to_action(cur, target2)]

    def choose_next_plan(self, cur):
        cx,cy=cur

        if (self.goal in self.safe) and self.should_exit_now(cur):#看看是不是该溜了，如果拿了金子或者太危险就撤
            return self.plan_to(cur,self.goal)

        unvisited_safe=[p for p in self.safe if p not in self.visited]#先把那种知道安全但还没去过的格子踩一下
        if unvisited_safe:
            best= None
            best_cost= None
            best_path= None
            for p in unvisited_safe:
                path = self.bfs_path(cur, p, self.safe | set([cur]))
                if not path:
                    continue
                d = len(path) - 1

                tie= abs(p[0] - self.goal[0]) + abs(p[1] - self.goal[1])#距离一样就选离终点近的
                cost=(d, tie)
                if best_cost is None or cost < best_cost:
                    best= p
                    best_cost=cost
                    best_path=path
            if best is not None:
                actions=[]
                for i in range(1,len(best_path)):
                    actions.append(self.to_action(best_path[i-1],best_path[i]))
                return actions


        global_total,pit_cnt,wum_cnt, useful_count=self.guess_risk_byBFs()#没软柿子，只能看看边缘格子的风险
        frontier =self.frontier_unknown()
        if global_total==0:
            if self.goal in self.safe:
                return self.plan_to(cur, self.goal)
            return []

        guaranteed_empty = []
        shoot_safe = []#有怪但无坑，可考虑射击后进入
        for c in frontier:
            pc=pit_cnt.get(c,0)
            wc =wum_cnt.get(c,0)
            if pc==0 and wc==0:
                guaranteed_empty.append(c)
            elif pc ==0 and wc>0:
                shoot_safe.append(c)

        for c in guaranteed_empty:
            self.safe.add(c)#推断出无怪，加入

        if (self.goal in self.safe) and self.should_exit_now(cur):#更新完名单后再确认是不是能走了
            return self.plan_to(cur,self.goal)

        if guaranteed_empty:#安全
            guaranteed_empty.sort(key=lambda p: (-useful_count.get(p,0),abs(p[0]-cx)+abs(p[1]-cy)))#优先去能提供更多线索的，其次离我近的
            target= guaranteed_empty[0]
            return self.plan_to(cur,target)

        if shoot_safe and self.arrows_left>0:
            shoot_safe.sort(key=lambda p: (-useful_count.get(p, 0), abs(p[0] - cx) + abs(p[1] - cy)))
            for target in shoot_safe:
                bases = [n for n in self.neighbors(*target) if n in self.safe]
                best_base = None
                best_path = None
                for b in bases:
                    path = self.bfs_path(cur, b, self.safe | set([cur]))
                    if not path:
                        continue
                    if best_path is None or len(path) < len(best_path):
                        best_base = b
                        best_path = path
                if best_base is None:
                    continue
                actions = []
                for i in range(1, len(best_path)):
                    actions.append(self.to_action(best_path[i - 1], best_path[i]))
                actions.append(Agent.Action.SHOOT)
                actions.append(self.to_action(best_base, target))
                return actions

        if self.goal in self.safe:#没地去了，如果终点安全就去终点
            return self.plan_to(cur, self.goal)

        if (self.arrows_left>0) and (self.goal in frontier) and (pit_cnt.get(self.goal,1)==0)and(wum_cnt.get(self.goal,0)> 0):
            #如果终点被怪占了但没坑，去杀它再撤
            bases =[n for n in self.neighbors(*self.goal) if n in self.safe]
            best_base= None
            best_path=None
            for b in bases:
                path =self.bfs_path(cur,b,self.safe | set([cur]))
                if not path:
                    continue
                if best_path is None or len(path)<len(best_path):
                    best_base= b
                    best_path=path
            if best_base is not None:
                actions= []
                for i in range(1, len(best_path)):
                    actions.append(self.to_action(best_path[i-1], best_path[i]))
                actions.append(Agent.Action.SHOOT)
                actions.append(self.to_action(best_base,self.goal))
                return actions
        return []



    def getAction(self, AgentX, AgentY, stench, breeze, glitter, bump, scream):
        cur=(AgentX, AgentY)

        prev_pos= self.prev_pos#记录并更新上一回合位置（用于检测两格往返）
        self.prev_pos= cur

        self.update_knowledge(cur, stench, breeze, scream)

        if glitter:
            self.has_gold= True
            return Agent.Action.GRAB

        if cur==self.goal and (self.has_gold or self.should_exit_now(cur)):#有金子或判断该撤离就爬
            return Agent.Action.CLIMB

        if self.action_queue:#继续走actionqueue
            act =self.action_queue.pop(0)
            if act==Agent.Action.SHOOT and self.arrows_left>0:
                self.arrows_left-= 1
            return act



        plan =self.choose_next_plan(cur)#重新规划
        if plan:
            self.action_queue=plan
            act=self.action_queue.pop(0)
            if act==Agent.Action.SHOOT and self.arrows_left> 0:
                self.arrows_left -=1
            return act



        if self.goal in self.safe:#兜底1，如果终点安全，尽量去终点
            plan =self.plan_to(cur, self.goal)
            if plan:
                self.action_queue = plan
                act= self.action_queue.pop(0)
                if act== Agent.Action.SHOOT and self.arrows_left>0:
                    self.arrows_left -=1
                return act


        safe_neighbors = [n for n in self.neighbors(*cur) if n in self.safe]#兜底2,选择安全的邻居
        if safe_neighbors:
            def prio(n):
                back= 1 if (prev_pos is not None and n== prev_pos) else 0
                unv= 0 if n not in self.visited else 1
                #邻接未知边界优先，因为能带来新信息
                touch_frontier= 0 if any(
                    (m not in self.safe) and (m not in self.que_pits) and (m not in self.que_wumpus) and (
                                m not in self.dead_wumpus)
                    for m in self.neighbors(*n)
                ) else 1
                dist= abs(n[0]-self.goal[0])+abs(n[1]-self.goal[1])
                return (back,unv,touch_frontier,dist)


            safe_neighbors.sort(key=prio)
            chosen = safe_neighbors[0]

            unknown_neighbor_exists = any(
                (n not in self.safe) and (n not in self.que_pits) and (n not in self.que_wumpus) and (n not in self.dead_wumpus)for n in self.neighbors(*cur)
            )

            # 在兜底阶段：若有未知邻居，累积“卡住”计数；否则清零
            if unknown_neighbor_exists:
                self.stuck =min(self.stuck + 1, 10)
            else:
                self.stuck= 0

            # 触发有界风险探测，被迫回头or连续卡住达到3次
            trigger_probe= unknown_neighbor_exists and (
                    (prev_pos is not None and chosen== prev_pos) or (self.stuck>=2)
            )

            if trigger_probe:
                pit_threshold= min(
                    self.PIT_THRESHOLD_MAX,
                    self.PIT_THRESHOLD_BASE+self.PIT_THRESHOLD_STEP*self.stuck
                )
                probe = self.decide_probe_action(cur, pit_threshold=pit_threshold)
                if probe:
                    self.action_queue =probe[1:]
                    act=probe[0]
                    if act== Agent.Action.SHOOT and self.arrows_left > 0:
                        self.arrows_left -= 1
                    return act

            return self.to_action(cur, chosen)


        if cur==self.goal:#兜底3，在终点直接撤
            return Agent.Action.CLIMB

        return Agent.Action.GRAB#兜底4，实在没办法了，原地占位