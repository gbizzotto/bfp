# Brainfuck VM by Gabriel.Bizzotto at gmail
# TODO:
# - fix the "cat code | python bf.py" with no ! in code hanging problm
# - more optimization
# BFBench:
# - factor.b:          9.6s (time echo "123456789" |  python bf.py factor.b)
# - mandelbrot:      2m39
# - si ! si ! hi123: 9m55

import os.path
import sys
import select

def replace_subsequence_once(l,a,b):
   done = 0
   for i in range(len(l)):
      if(l[i:i+len(a)] == a):
         l[i:i+len(a)] = b
         done += 1
   return done

def replace_subsequence(l,a,b):
   while replace_subsequence_once(l,a,b):
      pass

def RunInline(bf, print_code, filename):
   code = "# " + filename + "\n\n"
   code += """import sys

#@profile
def ok():
   d = [0] * 10000
   p = 0
   lend = 1000

"""
   lenbf = len(bf)
   pc = 0
   depth = 1
   while pc < lenbf:
      inst = bf[pc]
      v = 1
      if inst in ['+', '-', '<', '>']:
         p_local = 0 
         add_map = {}
         set_map = {}
         set_map_reverse = {}
         v = 0
         while inst in ['<', '>', '+', '-', 'z']:
            if inst == '<':
               p_local -= 1
               v += 1
            elif inst == '>':
               p_local += 1
               v += 1
            elif inst == '-':
               if p_local not in add_map.keys():
                  add_map[p_local] = -1
               else:
                  add_map[p_local] -= 1
               v += 1
            elif inst == '+':
               if p_local not in add_map.keys():
                  add_map[p_local] = 1
               else:
                  add_map[p_local] += 1
               v += 1
            elif inst == 'z':
               local_sum = 0
               v += 1
               while pc+v < lenbf and bf[pc+v] in ['+','-']:
                  if bf[pc+v] == '+':
                     local_sum += 1
                  else:
                     local_sum -= 1
                  v += 1
               set_map[p_local] = local_sum
               if local_sum not in set_map_reverse.keys():
                  set_map_reverse[local_sum] = [p_local];
               else: 
                  set_map_reverse[local_sum].append(p_local);
               if p_local in add_map.keys():
                  del add_map[p_local]
            if pc+v < lenbf:
               inst = bf[pc+v]
            else:
               inst = ' '
         for value, keys in set_map_reverse.iteritems():   
            keys.sort()
            following = 0
            for i in range(1,len(keys)):
               following += 1
               if keys[i] != keys[i-1]+1:
                  if following >= 2:
                     code += "   "*depth
                     code += "d[p+"+str(keys[i-following])+":p+"+str(keys[i-1]+1)+"] = ["+str(value)+"] * "+str(following)+"\n"
                     for j in range(keys[i-following], keys[i-following]+following):
                        del set_map[j]
                  following = 0
            else: 
               following += 1
               if following >= 3 and keys[-following]>=1:
                  code += "   "*depth
                  code += "d[p+"+str(keys[-following])+":p+"+str(keys[-1]+1)+"] = ["+str(value)+"] * "+str(following)+"\n"
                  for j in range(keys[-following], keys[-following]+following):
                     del set_map[j]
         for key, value in set_map.iteritems():
            if key != p_local:
               code += "   "*depth
               if key == 0:
                  code += "d[p] = "+str(value)+"\n"
               else:
                  code += "d[p+"+str(key)+"] = "+str(value)+"\n"
         for key, value in add_map.iteritems():
            if value != 0 and key != p_local:
               code += "   "*depth
               if key == 0:
                  code += "d[p] = (d[p] + "+str(value)+")&255\n"
               else:
                  code += "d[p+"+str(key)+"] = (d[p+"+str(key)+"] + "+str(value)+")&255\n"
         if p_local != 0:
            code += "   "*depth
            code += "p += " + str(p_local) + "\n"
         if p_local in set_map.keys():
            code += "   "*depth
            code += "d[p] = "+str(set_map[p_local])+"\n"
         if p_local in add_map.keys():
            code += "   "*depth
            code += "d[p] = (d[p] + "+str(add_map[p_local])+")&255\n"
      elif inst == ']':
         depth -= 1
         local_sum = 0
         while pc+v < lenbf and bf[pc+v] in ['+','-']:
            if bf[pc+v] == '+':
               local_sum += 1
            else:
               local_sum -= 1
            v += 1
         if local_sum != 0:
            mask = ""
            if local_sum < 0 or local_sum > 255:
               mask = "&255"
            code += "   "*depth
            code += "d[p] = "+str(local_sum)+mask+"\n"
      elif inst == '[':
         p_local = 0 
         add_map = {}
         zero_set = set()
         while bf[pc+v] in ['<', '>', '+', '-', 'z']:
            if bf[pc+v] == '<':
               p_local -= 1
            elif bf[pc+v] == '>':
               p_local += 1
            elif bf[pc+v] == '-':
               if p_local not in add_map.keys():
                  add_map[p_local] = -1
               else:
                  add_map[p_local] -= 1
            elif bf[pc+v] == '+':
               if p_local not in add_map.keys():
                  add_map[p_local] = 1
               else:
                  add_map[p_local] += 1
            elif bf[pc+v] == 'z':
               zero_set.add(p_local)
               if p_local in add_map.keys():
                  del add_map[p_local]
            v += 1
         is_an_add = p_local in zero_set
         if bf[pc+v] == ']' and len(add_map) == 0 and (len(zero_set) == 0 or (len(zero_set)==1 and 0 in zero_set and (p_local == 1 or p_local == -1))) and (p_local == 1 or p_local < 0):
            # seek loop [>] or [<]
            local_sum = 0
            v += 1
            while pc+v < lenbf and bf[pc+v] in ['>','<']:
               if bf[pc+v] == '>':
                  local_sum += 1
               else:
                  local_sum -= 1
               v += 1
            if p_local == 1:
               # [>]
               if len(zero_set) == 0:
                  code += "   "*depth
                  if local_sum == 0:
                     code += "p += d[p:].index(0)\n"
                  else:
                     code += "p += d[p:].index(0) + "+str(local_sum)+"\n"
               else:
                  code += "   "*depth
                  code += "tmp = p + d[p:].index(0)\n"
                  code += "   "*depth
                  code += "d[p:tmp] = [0] * (tmp-p)\n"
                  if local_sum == 0:
                     code += "p = tmp\n"
                  else:
                     code += "p = tmp + "+str(local_sum)+"\n"
            else:
               # [<]
               if len(zero_set) == 0:
                  code += "   "*depth
                  if local_sum == 0:
                     code += "p -= d[p::"+str(p_local)+"].index(0)*"+str(-p_local)+"\n"
                  else:
                     code += "p -= d[p::"+str(p_local)+"].index(0)*"+str(-p_local)+" + "+str(-local_sum)+"\n"
               else:
                  code += "   "*depth
                  code += "dd=d[:p+1]\n"
                  code += "   "*depth
                  code += "dd.reverse()\n"
                  code += "   "*depth
                  code += "tmp = p - dd.index(0)\n"
                  code += "   "*depth
                  code += "d[tmp+1:p+1] = [0] * (p-tmp)\n"
                  code += "   "*depth
                  if local_sum == 0:
                     code += "p = tmp\n"
                  else:
                     code += "p = tmp + "+str(-local_sum)+"\n"
         elif bf[pc+v] == ']' and (is_an_add or (p_local == 0 and 0 in add_map.keys() and add_map[0] == -1)):
            # add map or mul map
            code += "   "*depth
            code += "if d[p] != 0:\n"
            depth += 1
            for k in zero_set:
               if k != p_local:
                  code += "   "*depth
                  if k == 0:
                     code += "d[p] = 0\n"
                  else:
                     code += "d[p+"+str(k)+"] = 0\n"
            for k in add_map.keys():
               if k != p_local:
                  if k in zero_set:
                     # this value is set
                     code += "   "*depth
                     if k == 0:
                        code += "d[p] = " + str(add_map[0]) + "&255\n"
                     else:
                        code += "d[p+"+str(k)+"] = " + str(add_map[k]) + "&255\n"
                  elif is_an_add:
                     code += "   "*depth
                     if k == 0:
                        code += "d[p] = (d[p]+"+str(add_map[0])+")&255\n"
                     else:
                        code += "d[p+"+str(k)+"] = (d[p+"+str(k)+"]+"+str(add_map[k])+")&255\n"
                  else:
                     # is a mul
                     code += "   "*depth
                     if add_map[k] == 1:
                        code += "d[p+"+str(k)+"] = (d[p+"+str(k)+"]+d[p])&255\n"
                     else:
                        if add_map[k] == 1:
                           code += "d[p+"+str(k)+"] = (d[p+"+str(k)+"]+d[p])&255\n"
                        elif add_map[k] == -1:
                           code += "d[p+"+str(k)+"] = (d[p+"+str(k)+"]-d[p])&255\n"
                        else:
                           code += "d[p+"+str(k)+"] = (d[p+"+str(k)+"]+d[p]*"+str(add_map[k])+")&255\n"
            v += 1
            local_sum = 0
            while pc+v < lenbf and bf[pc+v] in ['+','-']:
               if bf[pc+v] == '+':
                  local_sum += 1
               else:
                  local_sum -= 1
               v += 1
            if p_local != 0:
               code += "   "*depth
               code += "p += "+str(p_local)+"\n"
            if local_sum != 0:
               mask = ""
               if mask < 0 or mask > 255:
                  mask = "&255"
               depth -= 1
               code += "   "*depth
               if p_local == 0:
                  code += "d[p] = "+str(local_sum)+mask+"\n"
               else:
                  code += "d[p+"+str(p_local)+"] = "+str(local_sum)+mask+"\n"
            else:
               code += "   "*depth
               if p_local == 0:
                  code += "d[p] = 0\n"
               else:
                  code += "d[p+"+str(p_local)+"] = 0\n"
               depth -= 1
         else:
            code += "   "*depth
            code += "while d[p] != 0:\n"
            depth += 1
            v = 1
      elif inst == 'z':
         local_sum = 0
         while pc+v < lenbf and bf[pc+v] in ['+','-']:
            if bf[pc+v] == '+':
               local_sum += 1
            else:
               local_sum -= 1
            v += 1
         code += "   "*depth
         code += "d[p] = "+str(local_sum)+"\n"
      elif inst == ',':
         code += "   "*depth
         code += "try:"
         code += "   "*(depth+1)
         code += "d[p] = ord(sys.stdin.read(1))\n"
         code += "   "*depth
         code += "except:"
         code += "   "*(depth+1)
         code += "d[p] = 0\n"
      elif inst == '.':
         code += "   "*depth
         code += "sys.stdout.write(chr(d[p]))\n"
      code += "   "*depth
      code += "# "
      for c in bf[pc:pc+v]:
         code += c
      code += "\n"
      pc += v
   depth -= 1
   code += "\n\n"
   code += "   "*depth
   code += "ok()\n"
   if print_code:
      print(code)
   else:
      exec(code)

def ReadCode(filename):
   result = []
   with open(filename, "r") as f:
      code = f.read()
   for c in code:
      if c in ['+','-','<','>','[',']','.',',']:
         result.append(c)
   return result

def Optimize(code):
   replace_subsequence(code, ['+','-'], [])
   replace_subsequence(code, ['-','+'], [])
   replace_subsequence(code, ['<','>'], [])
   replace_subsequence(code, ['>','<'], [])
   replace_subsequence(code, ['[','-',']'], ['z'])
   replace_subsequence(code, ['[','+',']'], ['z'])
   replace_subsequence(code, ['z','z'], ['z'])
   replace_subsequence(code, [']','z'], [']'])
   replace_subsequence(code, ['+',','], [','])
   replace_subsequence(code, ['-',','], [','])
   replace_subsequence(code, ['z',','], [','])
   return code

def main(argv):
   """mvm.py"""
   
   code = []
   for s in filter(os.path.isfile, argv):
      filename = s
      code = ReadCode(s)
      break
   else:
      filename = "<stdin>"
      # read code from input
      c = ' '
      while c != '!':
         c = sys.stdin.read(1)
         if c in ['+','-','<','>','[',']','.',',']:
            code.append(c)
   code = Optimize(code)
   RunInline(code, "-c" in argv, filename)
      

if __name__ == "__main__":
   main(sys.argv[1:])

