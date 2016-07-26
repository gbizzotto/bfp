
import sys

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
def RunInline(bf, fin):
   code = """memory = [0] * 10000
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
         code += "memory[pointer] = memory[pointer]+"+str(v)+"\n"
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
         code += "memory[pointer] = memory[pointer]-"+str(v)+"\n"
      elif inst == ']':
         if pc > 0 and bf[pc-1] != ']':
            code += "   "*depth
            code += "memory[pointer] %= 256\n"
         depth -= 1
      elif inst == '[':
         if pc > 0 and bf[pc-1] != '[':
            code += "   "*depth
            code += "memory[pointer] %= 256\n"
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
         is_an_if = False#pointer_local in zero_set
         if bf[pc+v] == ']' and is_an_if:
            # add if
            code += "   "*depth
            code += "if memory[pointer] != 0:\n"
            depth += 1
            for k in zero_set:
               if k != pointer_local:
                  code += "   "*depth
                  code += "memory[pointer+"+str(k)+"] = 0\n"
            for k in add_map.keys():
               if k != pointer_local:
                  code += "   "*depth
                  code += "memory[pointer+"+str(k)+"] = memory[pointer+"+str(k)+"] + "+str(add_map[k])+"\n"
            if pointer_local != 0:
               code += "   "*depth
               code += "pointer += " + str(pointer_local) + "\n"
            code += "   "*depth
            code += "memory[pointer] = 0\n"
            depth -= 1
            v += 1
         elif bf[pc+v] == ']' and pointer_local == 0 and 0 in add_map.keys() and add_map[0] == -1:
            # mul map
            code += "   "*depth
            code += "if memory[pointer] != 0:\n"
            depth += 1
            for k in zero_set:
               if k != pointer_local:
                  code += "   "*depth
                  code += "memory[pointer+"+str(k)+"] = 0\n"
            for k in add_map.keys():
               if k != pointer_local:
                  if k in zero_set:
                     code += "   "*depth
                     code += "memory[pointer+"+str(k)+"] = " + str(add_map[k]) + "\n"
                  else:
                     code += "   "*depth
                     code += "memory[pointer+"+str(k)+"] = memory[pointer+"+str(k)+"] + memory[pointer]*"+str(add_map[k])+"\n"
            code += "   "*depth
            code += "memory[pointer] = 0\n"
            depth -= 1
            v += 1
         else:
            code += "   "*depth
            code += "while memory[pointer] != 0:\n"
            depth += 1
            v = 1
      elif inst == 'z':
         code += "   "*depth
         code += "memory[pointer] = 0\n"
      elif inst == ',':
         code += "   "*depth
         code += "memory[pointer] = ord(fin.read(1))\n"
      elif inst == '.':
         code += "   "*depth
         code += "sys.stdout.write(chr(memory[pointer]))\n"
      pc += v
   print(code)
   exec(code)

#@profile
def Run(code, fin):
   memory = [0]
   pointer = 0
   pc = 0
   loopstack = []
   lencode = len(code)
   lenmemory = 1
   while pc < lencode:
      inst = code[pc]
      if inst == '+':
         memory[pointer] = (memory[pointer]+1)%256
      elif inst == '>':
         pointer += 1
         if pointer >= lenmemory:
            memory.append(0)
            lenmemory += 1
      elif inst == '<':
         pointer -= 1
      elif inst == '-':
         memory[pointer] = (memory[pointer]-1)%256
      elif inst == ']':
         if memory[pointer] != 0:
            pc = loopstack[-1]
         else:
            loopstack.pop()
      elif inst == '[':
         if memory[pointer] != 0:
            loopstack.append(pc)
         else:
            skip = 1
            while skip > 0 and pc < lencode:
               pc += 1
               if code[pc] == '[':
                  skip += 1
               elif code[pc] == ']':
                  skip -= 1
      elif inst == 'z':
         memory[pointer] = 0
      elif inst == ',':
         memory[pointer] = ord(fin.read())
      elif inst == '.':
         sys.stdout.write(chr(memory[pointer]))
      pc += 1

def ReadCode(filename):
   result = []
   with open(filename, "r") as f:
      code = f.read()
   for c in code:
      if c in ['+','-','<','>','[',']','.',',']:
         result.append(c)
   replace_subsequence(result, ['+','-'], [])
   replace_subsequence(result, ['-','+'], [])
   replace_subsequence(result, ['<','>'], [])
   replace_subsequence(result, ['>','<'], [])
   replace_subsequence(result, [']','[','-',']'], [']'])
   replace_subsequence(result, [']','[','+',']'], [']'])
   replace_subsequence(result, ['[','-',']'], ['z'])
   replace_subsequence(result, ['[','-',']','z'], ['z'])
   replace_subsequence(result, ['[','+',']','z'], ['z'])
   replace_subsequence(result, ['+',','], [','])
   replace_subsequence(result, ['-',','], [','])
   replace_subsequence(result, ['z',','], [','])

   return result

def main(argv):
   """mvm.py"""
   
   if len(argv) == 0:
      print("Use: python test.py <file>")
      return
   
   code = ReadCode(argv[0])
#   Run(code, sys.stdin)
   RunInline(code, sys.stdin)
   

if __name__ == "__main__":
   main(sys.argv[1:])

