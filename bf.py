# Brainfuck VM by Gabriel.Bizzotto at gmail
# TODO:
# - fix the "cat code | python bf.py" with no ! in code hanging problm
# - more optimization
# BFBench:
# - beer.b:     0m00.06s
# - factor.b:   0m18.50s (time echo "123456789" |  python bf.py factor.b)
# - mandelbrot: 4m57.00s

import os.path
import sys
from array import array 
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

#@profile
def RunInline(bf, fin, print_code, filename):
   code = ""
   #if (print_code):
   code += "# " + filename + "\n\n"
   code += """import sys
from array import array 

fin = sys.stdin
"""
   code += """memory = array('B', [0] * 10000)
pointer = 0
lenmemory = 1000

"""
   lenbf = len(bf)
   pc = 0
   depth = 0
   while pc < lenbf:
      inst = bf[pc]
      v = 1
      if inst == '+':
         while pc+v < lenbf and bf[pc+v] == inst:
            v += 1
         code += "   "*depth
         code += "memory[pointer] = (memory[pointer]+"+str(v)+")&255\n"
      elif inst == '>':
         while pc+v < lenbf and bf[pc+v] == inst:
            v += 1
         code += "   "*depth
         code += "pointer += "+str(v)+"\n"
#         code += "   "*depth
#         code += "if pointer >= lenmemory:\n"
#         code += "   "*depth
#         code += "   memory += [0] * 1000\n"
#         code += "   "*depth
#         code += "   lenmemory += 1000\n"
      elif inst == '<':
         while pc+v < lenbf and bf[pc+v] == inst:
            v += 1
         code += "   "*depth
         code += "pointer -= "+str(v)+"\n"
      elif inst == '-':
         while pc+v < lenbf and bf[pc+v] == inst:
            v += 1
         code += "   "*depth
         code += "memory[pointer] = (memory[pointer]-"+str(v)+")&255\n"
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
            code += "memory[pointer] = "+str(local_sum)+mask+"\n"
      elif inst == '[':
         pointer_local = 0 
         add_map = {0: 0}
         zero_set = set()
         while bf[pc+v] != ']' and bf[pc+v] in ['<', '>', '+', '-', 'z']:
            if bf[pc+v] == '<':
               pointer_local -= 1
            elif bf[pc+v] == '>':
               pointer_local += 1
            elif bf[pc+v] == '-':
               if pointer_local not in add_map.keys():
                  add_map[pointer_local] = -1
               else:
                  add_map[pointer_local] -= 1
            elif bf[pc+v] == '+':
               if pointer_local not in add_map.keys():
                  add_map[pointer_local] = 1
               else:
                  add_map[pointer_local] += 1
            elif bf[pc+v] == 'z':
               zero_set.add(pointer_local)
               if pointer_local in add_map.keys():
                  del add_map[pointer_local]
            v += 1
         is_an_add = pointer_local in zero_set
         if bf[pc+v] == ']' and (is_an_add or (pointer_local == 0 and 0 in add_map.keys() and add_map[0] == -1)):
            # add map or mul map
            code += "   "*depth
            code += "if memory[pointer] != 0:\n"
            depth += 1
            for k in zero_set:
               if k != pointer_local:
                  code += "   "*depth
                  if k == 0:
                     code += "memory[pointer] = 0\n"
                  else:
                     code += "memory[pointer+"+str(k)+"] = 0\n"
            for k in add_map.keys():
               if k != pointer_local:
                  if k in zero_set:
                     # this value is set
                     code += "   "*depth
                     if k == 0:
                        code += "memory[pointer] = " + str(add_map[0]) + "&255\n"
                     else:
                        code += "memory[pointer+"+str(k)+"] = " + str(add_map[k]) + "&255\n"
                  elif is_an_add:
                     code += "   "*depth
                     if k == 0:
                        code += "memory[pointer] = (memory[pointer]+"+str(add_map[0])+")&255\n"
                     else:
                        code += "memory[pointer+"+str(k)+"] = (memory[pointer+"+str(k)+"]+"+str(add_map[k])+")&255\n"
                  else:
                     # is a mul
                     code += "   "*depth
                     if add_map[k] == 1:
                        code += "memory[pointer+"+str(k)+"] = (memory[pointer+"+str(k)+"]+memory[pointer])&255\n"
                     else:
                        code += "memory[pointer+"+str(k)+"] = (memory[pointer+"+str(k)+"]+memory[pointer]*"+str(add_map[k])+")&255\n"
            v += 1
            local_sum = 0
            while pc+v < lenbf and bf[pc+v] in ['+','-']:
               if bf[pc+v] == '+':
                  local_sum += 1
               else:
                  local_sum -= 1
               v += 1
            if pointer_local != 0:
               code += "   "*depth
               code += "pointer += "+str(pointer_local)+"\n"
            if local_sum != 0:
               mask = ""
               if mask < 0 or mask > 255:
                  mask = "&255"
               depth -= 1
               code += "   "*depth
               if pointer_local == 0:
                  code += "memory[pointer] = "+str(local_sum)+mask+"\n"
               else:
                  code += "memory[pointer+"+str(pointer_local)+"] = "+str(local_sum)+mask+"\n"
            else:
               code += "   "*depth
               if pointer_local == 0:
                  code += "memory[pointer] = 0\n"
               else:
                  code += "memory[pointer+"+str(pointer_local)+"] = 0\n"
               depth -= 1
         else:
            code += "   "*depth
            code += "while memory[pointer] != 0:\n"
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
         code += "memory[pointer] = "+str(local_sum)+"\n"
      elif inst == ',':
         code += "   "*depth
         code += "memory[pointer] = ord(fin.read(1))\n"
      elif inst == '.':
         code += "   "*depth
         code += "sys.stdout.write(chr(memory[pointer]))\n"
      #if print_code:
      code += "   "*depth
      code += "# "
      for c in bf[pc:pc+v]:
         code += c
      code += "\n"
      pc += v
   if print_code:
      print(code)
   else:
      exec(code)

def ReadCode(filename):
   result = []
   with open(filename, "r") as f:
      code = array('c', f.read())
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
      code = ReadCode(s)
      filename = s
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
   RunInline(array('c',code), sys.stdin, "-c" in argv, filename)
      

if __name__ == "__main__":
   main(sys.argv[1:])

