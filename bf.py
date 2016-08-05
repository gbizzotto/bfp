# Brainfuck VM by Gabriel.Bizzotto at gmail
# TODO:
# - fix the "cat code | python bf.py" with no ! in code hanging problm
# - more optimization
# BFBench:
# - factor.b:          9.3s (time echo "123456789" |  python bf.py factor.b)
# - mandelbrot:      2m34
# - si ! si ! hi123: 5m13

import os.path
import sys
import select

memory_size = 10000

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
   code += "import sys\n\n"
   code += "#@profile\n"
   code += "def run_bf():\n"
   code += "   d = [0] * "+str(memory_size)+"\n"
   code += "   p = 0\n"
   code += "   lend = "+str(memory_size)+"\n\n"
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
         if bf[pc+v] == ']' and (is_an_add or (p_local == 0 and 0 in add_map.keys() and add_map[0] == -1)):
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
               if local_sum < 0 or local_sum > 255:
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
         code += "try:\n"
         code += "   "*(depth+1)
         code += "d[p] = ord(sys.stdin.read(1))\n"
         code += "   "*depth
         code += "except:\n"
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
   code += "run_bf()\n"
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
#   replace_subsequence(code, ['+','-'], [])
#   replace_subsequence(code, ['-','+'], [])
#   replace_subsequence(code, ['<','>'], [])
#   replace_subsequence(code, ['>','<'], [])
   replace_subsequence(code, ['[','-',']'], ['z'])
   replace_subsequence(code, ['[','+',']'], ['z'])
#   replace_subsequence(code, ['z','z'], ['z'])
   replace_subsequence(code, [']','z'], [']'])
   replace_subsequence(code, ['+',','], [','])
   replace_subsequence(code, ['-',','], [','])
   replace_subsequence(code, ['z',','], [','])
   return code

#################################################################################################
#################################################################################################
#################################################################################################
#################################################################################################

class Simple:
   def __init__(self, _p_local, _add_map, _zero_set):
      self.shift    = _p_local
      self.add_map  = _add_map
      self.zero_set = _zero_set
   def toString(self):
      return "shift: {0}, zeroes: {1}, adds: {2}".format(self.shift, self.zero_set, self.add_map)
   def __repr__(self):
      return self.toString()
   def __str__(self):
      return self.toString()
   def Mulable(self):
      return self.shift == 0 and len(self.zero_set) == 0 and 0 in self.add_map.keys() and self.add_map[0] == -1
   def Addable(self):
      return len(self.zero_set) == 1 and self.shift in self.zero_set and self.shift not in self.add_map.keys()

def Parse(bf, pc, lenbf, blocs):
   while pc < lenbf:
      inst = bf[pc]
      if inst in ['<', '>', '+', '-', 'z']:
         p_local, add_map, zero_set = 0, {}, set()
         while inst in ['<', '>', '+', '-', 'z']:
            if inst == '<':
               p_local -= 1
            elif inst == '>':
               p_local += 1
            elif inst == '-':
               if p_local not in add_map.keys():
                  add_map[p_local] = -1
               else:
                  add_map[p_local] -= 1
            elif inst == '+':
               if p_local not in add_map.keys():
                  add_map[p_local] = 1
               else:
                  add_map[p_local] += 1
            elif inst == 'z':
               zero_set.add(p_local)
               if p_local in add_map.keys():
                  del add_map[p_local]
            pc += 1
            if pc >= lenbf:
               break
            inst = bf[pc]
         blocs.append(Simple(p_local, add_map, zero_set))
      else:
         if inst == ',' or inst == '.':
            blocs.append(inst)
            pc += 1
         elif inst == '[':
            new_bloc_and_pc = Parse(bf, pc+1, lenbf, [])
            blocs.append(new_bloc_and_pc[0])
            pc = new_bloc_and_pc[1] + 1
         elif inst == ']':
            break
   return (blocs,pc)

def JITmulWithShifts(v, depth, will_set_cell):
   """build a mul operation"""
   code = "   "*depth
   code += "# mul with shifts\n"
   dp = "d[p]"
   if len(v.add_map) > 1:
      code += "   "*depth
      code += "tmp = d[p]\n"
      dp = "tmp"
   code += "   "*depth
   code += "if "+dp+" != 0:\n"
   depth += 1
   local_shift = 0
   for k,a in v.add_map.iteritems():
      if k != v.shift:
         if k != local_shift:
            code += "   "*depth
            code += "p += "+str(k-local_shift)+"\n"
            local_shift = k
         code += "   "*depth
         if a == 1:
            code += "d[p] = (d[p]+"+dp+")&255\n"
         elif a == -1:
            code += "d[p] = (d[p]-"+dp+")&255\n"
         else:
            code += "d[p] = (d[p]+"+dp+"*"+str(a)+")&255\n"
   if local_shift != 0:
      code += "   "*depth
      code += "p -= "+str(local_shift)+"\n"
   if not will_set_cell:
      code += "   "*depth
      code += "d[p] = 0\n"
   depth -= 1
   code += "   "*depth
   code += "# end mul\n"
   return code

def JITaddWithShifts(v, depth, will_set_cell):
   """build an add operation"""
   code = "   "*depth
   code += "# add with shifts\n"
   code += "   "*depth
   code += "if d[p] != 0:\n"
   depth += 1
   local_shift = 0
   for k,a in v.add_map.iteritems():
      if k != v.shift:
         if k != local_shift:
            code += "   "*depth
            code += "p += "+str(k-local_shift)+"\n"
            local_shift = k
         code += "   "*depth
         code += "d[p] = (d[p]+"+str(a)+")&255\n"
   if local_shift != v.shift:
      code += "   "*depth
      code += "p += "+str(v.shift-local_shift)+"\n"
   #if local_shift != 0:
   #   code += "   "*depth
   #   code += "p -= "+str(local_shift)+"\n"
   if not will_set_cell:
      code += "   "*depth
      code += "d[p] = 0\n"
   depth -= 1
   code += "   "*depth
   code += "# end add\n"
   return code

def JITsimpleWithShifts(v, depth, cell_is_zero):
   """JIT an instance of a Simple object"""
   #code = ""
   code = "   "*depth
   code += "# simple\n"
   for k in v.zero_set:
      if (v.shift == 0 or k != v.shift) and k not in v.add_map.keys():
         code += "   "*depth
         if k == 0:
            code += "d[p] = 0\n"
         else:
            code += "d[p+"+str(k)+"] = 0\n"
   local_shift = 0
   for k,a in v.add_map.iteritems():
      if v.shift == 0 or k != v.shift:
         if k != local_shift:
            code += "   "*depth
            code += "p += "+str(k-local_shift)+"\n"
            local_shift = k
         if k in v.zero_set or (k == 0 and cell_is_zero):
            # this value is set
            code += "   "*depth
            if a < 0 or a > 255:
               code += "d[p] = " + str(a) + "&255\n"
            else:
               code += "d[p] = " + str(a) + "\n"
         else:
            code += "   "*depth
            code += "d[p] = (d[p]+"+str(a)+")&255\n"
   if local_shift != v.shift:
      code += "   "*depth
      code += "p += "+str(v.shift-local_shift)+"\n"
   if v.shift != 0:
      if v.shift in v.zero_set:
         code += "   "*depth
         code += "d[p] = 0\n"
      if v.shift in v.add_map:
         code += "   "*depth
         code += "d[p] = (d[p] + " + str(v.add_map[v.shift]) +")&255\n"
   code += "   "*depth
   code += "# end simple\n"
   return code

def JITsub(tree, depth, cell_is_zero):
   code = ""
   for i,v in enumerate(tree):
      if v == ',':
         code += "   "*depth
         code += "try:\n"
         code += "   "*(depth+1)
         code += "d[p] = ord(sys.stdin.read(1))\n"
         code += "   "*depth
         code += "except:\n"
         code += "   "*(depth+1)
         code += "d[p] = 0\n"
         cell_is_zero = False
      elif v == '.':
         code += "   "*depth
         code += "sys.stdout.write(chr(d[p]))\n"
      elif isinstance(v, Simple):
         code += JITsimpleWithShifts(v, depth, cell_is_zero)
         cell_is_zero = (cell_is_zero and v.shift == 0 and 0 not in v.add_map.keys()) \
                      or(v.shift in v.zero_set and v.shift not in v.add_map.keys())
      elif isinstance(v, list):
         if not cell_is_zero:
            will_set_cell = i+1<len(tree) and isinstance(tree[i+1],Simple) and 0 in tree[i+1].add_map
            if len(v) == 1 and isinstance(v[0],Simple) and v[0].Mulable():
               code += JITmulWithShifts(v[0], depth, will_set_cell)
            elif len(v) == 1 and isinstance(v[0],Simple) and v[0].Addable():
               code += JITaddWithShifts(v[0], depth, will_set_cell)
            else:
               code += "   "*depth
               code += "while d[p] != 0:\n"
               code += JITsub(v, depth+1, False)
            cell_is_zero = True
            code += "   "*depth
            code += "# cell is zero\n"
   return code

# mandelbrot 2m35

def JIT(tree, filename):
   code = "# " + filename + "\n\n"
   code += "import sys\n\n"
   code += "#@profile\n"
   code += "def run_bf():\n"
   code += "   d = [0] * "+str(memory_size)+"\n"
   code += "   p = 0\n"
   code += "   lend = "+str(memory_size)+"\n\n"
   code += JITsub(tree, 1, True)
   code += "\n\nrun_bf()\n"
   return code

import pprint

def main(argv):
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
   #RunInline(code, "-c" in argv, filename)

   parsed_code = Parse(code, 0, len(code), [])[0]
   jitted_code = JIT(parsed_code, filename)
#   pp = pprint.PrettyPrinter(indent=4)
#   pp.pprint(parsed_code)
   if "-c" in argv:
      print jitted_code 
   else:
      exec(jitted_code)
      

if __name__ == "__main__":
   main(sys.argv[1:])

