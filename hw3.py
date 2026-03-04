import random
from Othello import Othello
import copy
import time
import multiprocessing

def player_move_fun_with_timeout(board, CanGo_list, title):
    #注：不能修改此函数，且提交的文件里必须有这个函数，不然直接0分
    try:
        # 创建队列用于传递结果
        result_queue = multiprocessing.Queue()
        # 创建进程，传递参数和结果队列
        process = multiprocessing.Process(target=player_move_fun, args=(board, CanGo_list, title,result_queue))
        # 启动进程
        process.start()
        # 等待五秒
        process.join(timeout=5)
        if process.is_alive():
            # 如果进程仍在运行，即超过了五秒，终止进程并返回 None
            process.terminate()
            process.join()
            raise Exception("time out")
        else:
            move = result_queue.get()
    except Exception as e:
        raise Exception("An error occurred:", str(e))

    return move

def player_move_fun(board, CanGo_list, title, result_queue=None):
    # you can only code here
    # 只能在这里写代码，其他的代码一律不能改动，可以忽略result_queue这个参数
    try:
        import time
        import random

        for mv in CanGo_list:#有角直接下，最好的位置
            if Othello.isOnCorner(mv[0], mv[1]):
                move =mv
                if not result_queue:
                    return move
                else:
                    result_queue.put(move)
                    return move

        if len(CanGo_list)==1:#只有一种走法，直接返回
            move=CanGo_list[0]
            if not result_queue:
                return move
            else:
                result_queue.put(move)
                return move

        start_time =time.time()
        TIME_LIMIT =4.5#内部做个时间限制

        class _TimeUp(Exception):
            pass

        def check_time():
            if time.time() - start_time > TIME_LIMIT:
                raise _TimeUp()

        def opponent(t):
            return 'white' if t == 'black' else 'black'

        DIRS = [(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1),(-1,0),( -1,1)]#一个子边上的八个位置，搜索根据
        CORNERS = {(0,0),(7,0),(0,7),(7,7)}
        X_SQUARES = {(1,1),(6,1),(1,6),(6,6)}
        C_SQUARES = {(0,1),(1,0),(7,1),(6,0),(0,6),(1,7),(7,6)}


        POS_W=[#边角权重拉满，除了c意外的边上的子也是，剩余的看情况给
            [120,-20,20,5,5,20,-20,120],
            [-20,-40,-5,-5,-5,-5,-40,-20],
            [20,-5,15,3,3,15,-5,20],
            [5,-5,3,2,2,3,-5,5],
            [5,-5,3,2,2,3,-5,5],
            [20,-5,15,3,3,15,-5,20],
            [-20,-40,-5,-5,-5,-5,-40,-20],
            [120,-20,20,5,5,20,-20,120],]
        CORNER_ADJ={#用于计算角邻惩罚
            (0,0): [(0,1),(1,0),(1,1)],
            (7,0): [(7,1),(6,0),(6,1)],
            (0,7): [(0,6),(1,7),(1,6)],
            (7,7): [(7,6),(6,7),(6,6)],
        }

        def count_empty(bd):
            return len(empties)

        def corner_empty_related(bd, x, y):#判断xORc位置所对应的角是否为空，排序惩罚用
            if (x,y)== (1,1):   return bd[0][0]=='none'
            if (x,y)== (6,1):   return bd[7][0]=='none'
            if (x,y)==(1,6):   return bd[0][7]== 'none'
            if (x,y)==(6,6):   return bd[7][7]== 'none'
            if (x,y) in {(0,1),(1,0)}: return bd[0][0]=='none'
            if (x,y) in {(7,1),(6,0)}: return bd[7][0]=='none'
            if (x,y) in {(0,6),(1,7)}: return bd[0][7]=='none'
            if (x,y) in {(7,6),(6,7)}: return bd[7][7]== 'none'
            return False

        def tiles_flip_fast(bd, tile, xstart, ystart):#避免深拷贝带来的性能开销，返回翻转了哪些棋
            if bd[xstart][ystart] !='none':
                return []
            other =opponent(tile)
            flips =[]
            for dx,dy in DIRS:#8个方向都试
                x,y=xstart+dx, ystart+dy
                line=[]
                while 0<=x<8 and 0<=y<8 and bd[x][y]==other:#不出界 不空 不为我的棋就不停
                    line.append((x, y))
                    x+=dx;y+=dy
                if line and 0 <=x<8 and 0<=y<8 and bd[x][y]==tile:
                    flips.extend(line)
            return flips


        empties=set((x,y) for x in range(8) for y in range(8) if board[x][y]=='none')#仅遍历空位，使用集合便于o1的增删

        def valid_move(bd, tile):
            res=[]
            for (x, y) in empties:#仅遍历空位，减少无效检查
                if bd[x][y] == 'none' and tiles_flip_fast(bd,tile,x,y):
                    res.append([x,y])
            return res


        def apply_move_inplace(bd, mv, tile, flips):# 在不copy棋盘的前提下，强行在bd上执行一步棋。
            x, y=mv
            bd[x][y]=tile
            empties.discard((x, y))#维护空位集合
            for fx,fy in flips:
                bd[fx][fy]=tile

        def undo_move_inplace(bd, mv, tile, flips):#撤回刚刚的操作k，用于递归返回
            x, y=mv
            bd[x][y]='none'
            empties.add((x,y))
            other=opponent(tile)
            for fx, fy in flips:
                bd[fx][fy] = other

        def evaluate(bd, me, my_m_len, op_m_len):#评估函数，最重要～
            you=opponent(me)
            pos=0
            me_num=you_num=0
            frontier_me=frontier_you=0#周围有空的子，一般来说不是好事，统计用
            emptynum=0



            for x in range(8):#遍历棋盘，搜集星系
                for y in range(8):
                    v=bd[x][y]
                    if v=='none':
                        emptynum +=1
                    elif v==me:
                        pos +=POS_W[x][y]#根据刚刚的分数矩阵加分
                        me_num +=1
                        for dx,dy in DIRS:#检查前沿子
                            nx,ny =x+dx,y+dy
                            if 0<=nx<8 and 0<=ny<8 and bd[nx][ny] == 'none':
                                frontier_me += 1
                                break
                    else:
                        pos -=POS_W[x][y]#减分
                        you_num +=1
                        for dx,dy in DIRS:
                            nx,ny =x+dx,y+dy
                            if 0<=nx<8 and 0<=ny<8 and bd[nx][ny]=='none':
                                frontier_you += 1
                                break


#角分，角邻的惩罚，机动性，前沿子得分计算，这里的分数进行动态加权（除了激动
            corner_diff =0#这里角分是不进行动态加权的，固定的30分，要注意
            for (cx,cy) in CORNERS:
                if bd[cx][cy]==me:
                    corner_diff +=1
                elif bd[cx][cy]==you:
                    corner_diff -=1
            corner_score=30 * corner_diff


            adj_score=0#角邻惩罚，不要随便走x或c位
            for c in CORNERS:
                cx,cy=c
                if bd[cx][cy]=='none':
                    for (ax,ay) in CORNER_ADJ[c]:
                        if bd[ax][ay]==me:
                            adj_score -=6
                        elif bd[ax][ay]==you:
                            adj_score +=6

            mobility =4*(my_m_len -op_m_len)#有多少走法，机动性


            frontier_term = -0.8*(frontier_me-frontier_you)#前沿子惩罚


            disc_diff=me_num-you_num#子的数量差



#动态加权，不同阶段每个位置重要性不同
            if emptynum >= 40:
                return 1.2*pos+ 1*mobility+ corner_score+ 0.1*disc_diff+frontier_term+adj_score#此时子差无关紧要，最重要的是位置分
            elif emptynum >= 20:
                return 1*pos+ 0.8*mobility + corner_score+0.6*disc_diff+0.5*frontier_term+adj_score
            else:
                return 0.6*pos+0.5*mobility+corner_score+2.0*disc_diff+0.3*frontier_term+adj_score#子差最重要，位置分和机动性没那么重要了




        def move_order (bd,moves,cur,root=False):#优化走法的排序,优先检索好走法 加速剪枝
            scored=[]
            for mv in moves:
                x,y=mv
                s=0
                if (x,y) in CORNERS:
                    s+=10000#走角第一个被检索出
                elif x==0 or x==7 or y==0 or y==7:
                    s+=300#边
                if (x,y) in X_SQUARES and corner_empty_related(bd,x,y):
                    s-=2000#x位
                if (x,y) in C_SQUARES and corner_empty_related(bd,x,y):
                    s-=1000#c位


                if root:#少翻子！！！翻的越多对面可以利用的也越多（？ 限制对面的机动性
                    flips = tiles_flip_fast(bd,cur,x,y)
                    s += -5* len(flips)
                s += history.get((cur, x, y), 0)#历史启发分（造成过剪枝的着法优先）
                scored.append((s, mv))

            scored.sort(key=lambda t: t[0], reverse=True)
            return [mv for _, mv in scored]



        def board_to_key(bd):
            return tuple(tuple(bd[x][y] for y in range(8)) for x in range(8))#把8x8的棋盘转成可哈希的三元组而不是不可哈希的list

        TT ={}#在搜索树的不同分支中碰到相同的状态时，直接从TT中读取结果
        TT_MAX = 60000#过大时就清空
        history ={}#历史启发

        def terminal_value(bd):
            sc=Othello.getScoreOfBoard(bd)
            return (sc[title]-sc[opponent(title)])*1000000 #结束时胜负优先，而不是未来

        def negamax(bd,depth,alpha,beta,cur):#alphabeta&negamax
            check_time()
            moves=valid_move(bd, cur)

            pos_key=None
            tt_best =None
            if depth >=2:#深度较深时再用，避免频繁建大key
                pos_key = (cur, board_to_key(bd))
                entry = TT.get(pos_key)
                if entry:
                    if entry[0] >=depth:#缓存深度够，直接返回分数
                        return entry[1]
                    tt_best=entry[2]#不够，仅借用entry2

            if depth==0:
                oppsite_moves=valid_move(bd, opponent(cur))
                if not moves and not oppsite_moves:
                    score=terminal_value(bd)#只有无棋可下时才判终，使用刚刚的胜负优先评判函数
                else:#未结束
                    if cur ==title:#对面走
                        score=evaluate(bd, title, len(moves), len(oppsite_moves))
                    else:
                        score=evaluate(bd, title, len(oppsite_moves), len(moves))
                if pos_key is not None:
                    if len(TT)>TT_MAX:
                        TT.clear()
                    TT[pos_key] = (depth, score, None)#叶子没有子，没最佳走法
                return score

            if not moves:#我无棋可下，即moves空
                opposite_moves =valid_move(bd, opponent(cur))#检查对手有没有棋可走
                if not opposite_moves:#gg了
                    score = terminal_value(bd)
                    if pos_key is not None:#存入置换表
                        if len(TT)>TT_MAX:
                            TT.clear()
                        TT[pos_key] = (depth, score, None)
                    return score

                val =-negamax(bd,depth,-beta,-alpha,opponent(cur))#深度不减，对面回合，把对面的分数取-就是我这回合不能动带来的分数值预估
                if pos_key is not None:
                    if len(TT)>TT_MAX:
                        TT.clear()
                    TT[pos_key] = (depth,val,None)
                return val

            best= -10**12#不在叶节点且有棋可走
            best_child_mv=None
            ordered =move_order(bd,moves,cur,root=False)#tt给提示了，把该这法到最前
            if tt_best and tt_best in ordered:
                ordered.remove(tt_best)
                ordered.insert(0, tt_best)

            for mv in ordered:
                check_time()  # 循环内也检查，避免长分支超时
                flips = tiles_flip_fast(bd, cur, mv[0], mv[1])
                apply_move_inplace(bd, mv, cur, flips)
                val = -negamax(bd, depth - 1, -beta, -alpha, opponent(cur))
                undo_move_inplace(bd, mv, cur, flips)

                if val > best:
                    best = val
                    best_child_mv = mv
                if best > alpha:
                    alpha = best
                if alpha >= beta:
                    hk = (cur, mv[0], mv[1])#历史启发回写，越深给分越多
                    history[hk] = history.get(hk, 0) + depth * depth
                    break

            if pos_key is not None:
                if len(TT) > TT_MAX:
                    TT.clear()
                TT[pos_key] = (depth, best, best_child_mv)
            return best

        empty_now =count_empty(board)
        if empty_now <= 12:
            depth_plan = [empty_now]#直接穷举到终局
        elif empty_now >=41:
            depth_plan=[4,5,6,7]#开局没必要考虑那么深
        elif empty_now >= 31:
            depth_plan =[4,5,6,7,8,9]#分的细一点
        elif empty_now>=21:
            depth_plan=[5,6,7,8,9,10]#中盘，考虑的深一点
        else:
            depth_plan=[6,7,8,9,10,11]#终局前段



        best_move =CanGo_list[0]#超时保险
        best_val= -10**18
        root_moves=move_order(board,list(CanGo_list),title,root=True)

        for d in depth_plan:
            try:
                check_time()
                current_best_mv=root_moves[0]
                current_best_val= -10**18
                for mv in root_moves:
                    check_time()
                    flips =tiles_flip_fast(board, title, mv[0], mv[1])
                    apply_move_inplace(board, mv, title, flips)
                    val = -negamax(board, d-1, -10**18, 10**18, opponent(title))
                    undo_move_inplace(board,mv,title,flips)

                    if val>current_best_val:
                        current_best_val=val
                        current_best_mv=mv
                best_move=current_best_mv
                best_val=current_best_val#一层d的迭代结束，存best


                if best_move in root_moves:#d+1时，将当前的best走法放在首位去搜索，极有可能是一个较大的alpha值，提升剪枝效率
                    root_moves.remove(best_move)
                    root_moves.insert(0, best_move)
            except _TimeUp:
                break

        move=best_move if best_move in CanGo_list else CanGo_list[0]

    except Exception:
        import random as _r
        _r.shuffle(CanGo_list)
        move=CanGo_list[0]

    # end code
    if not result_queue:
        return move
    else:
        result_queue.put(move)
        return move
