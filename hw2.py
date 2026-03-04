class Eight_Puzzle():


    class PathResult(list):
        def __init__(self, seq, solved):
            super().__init__(seq)
            self.solved = solved

        def __str__(self):
            if not self.solved or any(p is None for p in self):
                return "无解"
            steps = len(self) - 1
            lines = [f"步数：{steps}", "路径："]
            for i, m in enumerate(self):
                lines.append(f"Step {i}:")
                for row in m:
                    lines.append(" ".join(str(x) for x in row))
                lines.append("-" * 8)
            return "\n".join(lines)
        # ！！！不改变原有题目给定的demo，但使展示“无解”或“步数+路径矩阵”，且仍保留了列表的全部行为。如果要看到底层原始列表，可使用list(path)或print(list(path))

    def __init__(self):
        pass

    def solve(self, initial_matrix, target_matrix):
        path = []
        path.append(initial_matrix)

        # you can write code here
        # 假设path是：initial_matrix->matrix1->matrix2->matrix3->target_matrix,最终返回的path应该是[initial_matrix,matrix1,matrix2,matrix3,target_matrix]，若无解，则返回[initial_matrix,None,target_matrix]

        def copym(m):#深拷贝一下原list，方便操作
            r =[]
            for i in range(3):
                r.append(m[i][:])
            return r

        def keym(m):#把可变的list转为元组，用于映射copym和检测closed中的状态有没有被处理过等
            t =[]
            for i in range(3):
                for j in range(3):
                    t.append(m[i][j])
            return tuple(t)

        def find_zero(m):
            for i in range(3):
                for j in range(3):
                    if m[i][j]==0:
                        return i,j
            return -1, -1

        def inv_count(arr):#逆序对计算
            c =0
            n =len(arr)
            for i in range(n):
                for j in range(i+1,n):
                    if arr[i] >arr[j]:
                        c +=1
            return c

        def solvable(start,goal):#任何移动都不改变逆序对总数奇偶性，所以检测目标list和当前list的逆序对奇偶性是否一致即可
            s =[]
            g =[]
            for i in range(3):
                for j in range(3):
                    if start[i][j] !=0:
                        s.append(start[i][j])
                    if goal[i][j] !=0:
                        g.append(goal[i][j])
            return (inv_count(s) %2)==(inv_count(g)%2)

        def h_linear(m, goal_pos):
            man=0#先用曼哈顿距离
            for i in range(3):
                for j in range(3):
                    v =m[i][j]
                    if v!=0:
                        ti, tj=goal_pos[v]
                        man +=abs(i -ti)+abs(j-tj)

            row_conf =0#使用线性冲突弥补曼哈顿距离估算的误差
            #一对线性冲突之所以“至少+2”，是因为两块在同一行（或列）里无法互相越过，必须让其中一块离开该行（或列）再回来，带来两次垂直（或水平）绕行，这两步不在曼哈顿里。
            for i in range(3):
                arr =[]
                for j in range(3):
                    v =m[i][j]
                    if v!=0:
                        ti, tj=goal_pos[v]
                        if ti ==i:
                            arr.append(tj)
                row_conf +=inv_count(arr)

            col_conf =0#列
            for j in range(3):
                arr =[]
                for i in range(3):
                    v =m[i][j]
                    if v !=0:
                        ti, tj =goal_pos[v]
                        if tj ==j:
                            arr.append(ti)
                col_conf+=inv_count(arr)
            return man +2*(row_conf+col_conf)

        def reconstruct(parent, end_key,states):#一路回溯到起点
            keys =[]
            k =end_key
            while True:
                keys.append(k)
                if k not in parent:
                    break#找到了起点
                k =parent[k]
            keys.reverse()
            seq =[]
            for kk in keys:
                seq.append(copym(states[kk]))#从state得到元组key到list映射
            return seq

        if not solvable(initial_matrix,target_matrix):
            path.append(None)
        else:
            import heapq#优先队列

            start =copym(initial_matrix)
            goal =copym(target_matrix)
            goal_key =keym(goal)

            goal_position ={}
            for i in range(3):
                for j in range(3):
                    goal_position[goal[i][j]] =(i,j)#字典，每个数字的目标位置，就不用每次遍历goal

            open_list =[]
            count =0

            start_key = keym(start)
            g = {start_key: 0}
            parent ={}
            states ={start_key: start}
            h0 = h_linear(start, goal_position)
            heapq.heappush(open_list, (h0, count,start_key))
            closed =set()#存放所有已被处理过的key,防止重复搜。

            found=False
            while open_list:
                f,_,cur_key = heapq.heappop(open_list)
                if cur_key in closed:
                    continue
                if cur_key == goal_key:
                    sol_path = reconstruct(parent,cur_key,states) #含起点和终点
                    for idx in range(1, len(sol_path)-1):#只把中间状态加入path，起点在path[0]，终点会在函数尾加
                        path.append(sol_path[idx])
                    found =True
                    break

                closed.add(cur_key)
                cur =states[cur_key]
                zx, zy =find_zero(cur)

                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    nx,ny=zx +dx,zy +dy
                    if 0 <=nx<3 and 0<=ny<3:
                        nb = copym(cur)
                        nb[zx][zy],nb[nx][ny] =nb[nx][ny],nb[zx][zy]
                        nk =keym(nb)
                        newg =g[cur_key] +1
                        if nk not in g or newg <g[nk]:
                            g[nk] =newg
                            parent[nk] =cur_key
                            states[nk] =nb
                            count +=1
                            h = h_linear(nb, goal_position)
                            heapq.heappush(open_list, (newg+h,count,nk))

            if not found and (len(path) ==1 or path[-1] is not None):#若意外没找到，当无解
                path.append(None)

        # finish coding

        path.append(target_matrix)

        solved = not any(p is None for p in path)
        return self.PathResult(path, solved)

        #return path
#185行为代码原有的，如果不希望使用182和183行新增的代码，可以注释掉182，183，把这185的注释去掉，并注释class PathResult(list)后，print(path)直接显示原始结果，否则使用print(list(path))



# 你可以在Eight_Puzzle类中定义任何函数，只需要保证下面demo跑通即可，提交时只需要提交类的代码，下面代码可以注释掉
initial_matrix = [[2,8,3],[1,6,4],[7,0,5]]
target_matrix = [[1,2,3],[8,0,4],[7,6,5]]
problem = Eight_Puzzle()
path = problem.solve(initial_matrix,target_matrix)
print(path)

print(list(path))#底层原始列表，详情见开头class PathResult(list)的注释，可选择使用与否