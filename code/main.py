import os
import argparse

MemSize = 1000 # memory size, in reality, the memory size should be 2^32, but for this lab, for the space resaon, we keep it as this large number, but the memory is still 32-bit addressable.

def sign_extend(value, bits):
    if value >= (1 << (bits - 1)):
        value -= (1 << bits)
    return value

def decode(instr):
    opcode = instr[25:32] 
    funct7 = instr[0:7] 
    rs2 = int(instr[7:12], 2) 
    rs1 = int(instr[12:17], 2)
    funct3 = instr[17:20]
    rd = int(instr[20:25], 2) 
    imm_i = sign_extend(int(instr[0:12], 2), 12)
    imm_s = sign_extend(int(instr[0:7] + instr[20:25], 2), 12)
    imm_b = sign_extend(int(instr[0] + instr[24] + instr[1:7] + instr[20:24] + '0', 2), 13)
    imm_j = sign_extend(int(instr[0] + instr[12:20] + instr[11] + instr[1:11] + '0', 2), 21)
    return {"opcode": opcode, "funct7": funct7, "funct3": funct3, "rs1": rs1, "rs2": rs2, "rd": rd, "imm_i": imm_i, "imm_s": imm_s, "imm_b": imm_b, "imm_j": imm_j,}

def execute(decoded, rf):
    opcode = decoded["opcode"]
    funct3 = decoded["funct3"]
    funct7 = decoded["funct7"]
    rs1_val = rf.readRF(decoded["rs1"])
    rs2_val = rf.readRF(decoded["rs2"])
    rd = decoded["rd"]
    imm_i = decoded["imm_i"]
    imm_s = decoded["imm_s"]
    imm_b = decoded["imm_b"]
    imm_j = decoded["imm_j"]
    result = {"rd": rd, "wrt_enable": False, "rd_mem": False, "wrt_mem": False, "halt": False, "branch_taken": False, "branch_target": None, "alu_result": 0, "store_data": rs2_val, "mem_addr": 0,}
    if opcode == "0110011":
        result["wrt_enable"] = True
        if funct3 == "000":
            if funct7 == "0000000":
                result["alu_result"] = rs1_val + rs2_val
            elif funct7 == "0100000":
                result["alu_result"] = rs1_val - rs2_val
        elif funct3 == "100":
            result["alu_result"] = rs1_val ^ rs2_val
        elif funct3 == "110":
            result["alu_result"] = rs1_val | rs2_val
        elif funct3 == "111":
            result["alu_result"] = rs1_val & rs2_val
        result["alu_result"] = result["alu_result"] & 0xFFFFFFFF
    elif opcode == "0010011":
        result["wrt_enable"] = True
        if funct3 == "000":
            result["alu_result"] = rs1_val + imm_i
        elif funct3 == "100":
            result["alu_result"] = rs1_val ^ imm_i
        elif funct3 == "110":
            result["alu_result"] = rs1_val | imm_i
        elif funct3 == "111":
            result["alu_result"] = rs1_val & imm_i
        result["alu_result"] = result["alu_result"] & 0xFFFFFFFF
    elif opcode == "0000011":
        result["wrt_enable"] = True
        result["rd_mem"] = True
        result["mem_addr"] = rs1_val + imm_i
    elif opcode == "0100011":
        result["wrt_mem"] = True
        result["mem_addr"] = rs1_val + imm_s
        result["store_data"] = rs2_val
    elif opcode == "1100011":
        if funct3 == "000":
            taken = (rs1_val == rs2_val)
        elif funct3 == "001":
            taken = (rs1_val != rs2_val)
        else:
            taken = False
        result["branch_taken"] = taken
        result["branch_target"] = imm_b
    elif opcode == "1101111":
        result["wrt_enable"] = True
        result["branch_taken"] = True
        result["branch_target"] = imm_j
    elif opcode == "1111111":
        result["halt"] = True
    return result

class InsMem(object):
    def __init__(self, name, ioDir):
        self.id = name
        with open(ioDir + "\\imem.txt") as im:
            self.IMem = [data.replace("\n", "") for data in im.readlines()]
        while len(self.IMem) < MemSize:
            self.IMem.append("00000000")

    def readInstr(self, ReadAddress):
        byte0 = self.IMem[ReadAddress]
        byte1 = self.IMem[ReadAddress + 1]
        byte2 = self.IMem[ReadAddress + 2]
        byte3 = self.IMem[ReadAddress + 3]
        return byte0 + byte1 + byte2 + byte3
          
class DataMem(object):
    def __init__(self, name, ioDir):
        self.id = name
        self.ioDir = ioDir
        with open(ioDir + "\\dmem.txt") as dm:
            self.DMem = [data.replace("\n", "") for data in dm.readlines()]
        while len(self.DMem) < MemSize:
            self.DMem.append("00000000")

    def readInstr(self, ReadAddress):
        byte0 = self.DMem[ReadAddress]
        byte1 = self.DMem[ReadAddress + 1]
        byte2 = self.DMem[ReadAddress + 2]
        byte3 = self.DMem[ReadAddress + 3]
        return int(byte0 + byte1 + byte2 + byte3, 2)
        
    def writeDataMem(self, Address, WriteData):
        binary = format(WriteData & 0xFFFFFFFF, '032b')  
        self.DMem[Address] = binary[0:8]
        self.DMem[Address + 1] = binary[8:16]
        self.DMem[Address + 2] = binary[16:24]
        self.DMem[Address + 3] = binary[24:32]
                     
    def outputDataMem(self):
        resPath = self.ioDir + "\\" + self.id + "_DMEMResult.txt"
        with open(resPath, "w") as rp:
            rp.writelines([str(data) + "\n" for data in self.DMem])

class RegisterFile(object):
    def __init__(self, ioDir):
        self.outputFile = ioDir + "RFResult.txt"
        self.Registers = [0x0 for i in range(32)]
    
    def readRF(self, Reg_addr):
        return self.Registers[Reg_addr]
    
    def writeRF(self, Reg_addr, Wrt_reg_data):
        if Reg_addr != 0:
            self.Registers[Reg_addr] = Wrt_reg_data & 0xFFFFFFFF
         
    def outputRF(self, cycle):
        op = ["-" * 70 + "\n", "State of RF after executing cycle:" + str(cycle) + "\n"]
        for val in self.Registers:
            op.append(format(val & 0xFFFFFFFF, "032b") + "\n")
        perm = "w" if cycle == 0 else "a"
        with open(self.outputFile, perm) as file:
            file.writelines(op)

class State(object):
    def __init__(self):
        self.IF = {"nop": False, "PC": 0}
        self.ID = {"nop": False, "Instr": 0, "PC": 0}
        self.EX = {"nop": False, "Read_data1": 0,"Read_data2": 0, "Imm": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "is_I_type": False, "rd_mem": 0, "wrt_mem": 0, "alu_op": 0, "wrt_enable": 0}
        self.MEM = { "nop": False, "ALUresult": 0, "Store_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0, "rd_mem": 0, "wrt_mem": 0, "wrt_enable": 0 }
        self.WB = {"nop": False, "Wrt_data": 0, "Rs": 0, "Rt": 0, "Wrt_reg_addr": 0,  "wrt_enable": 0 }

class Core(object):
    def __init__(self, ioDir, imem, dmem):
        self.myRF = RegisterFile(ioDir)
        self.cycle = 0
        self.halted = False
        self.ioDir = ioDir
        self.state = State()
        self.nextState = State()
        self.ext_imem = imem
        self.ext_dmem = dmem

    def reportMetrics(self, core_name, ioDir, mode="w"):
        cycles = self.cycle
        insts  = self.inst_count
        ipc = insts / cycles if cycles > 0 else 0
        cpi = cycles / insts if insts > 0 else 0
        report = [f"Performance of {core_name}:", f"#Cycles -> {cycles}", f"#Instructions -> {insts}", f"CPI -> {cpi}", f"IPC -> {ipc}", "",]
        for line in report:
            print(line)

        metrics_path = ioDir + "\\PerformanceMetrics.txt"
        with open(metrics_path, mode) as f:
            f.write("\n".join(report) + "\n")

class SingleStageCore(Core):
    def __init__(self, ioDir, imem, dmem):
        super(SingleStageCore, self).__init__(ioDir + "\\SS_", imem, dmem)
        self.opFilePath = ioDir + "\\StateResult_SS.txt"
        self.inst_count = 0 

    def step(self):
        self.nextState = State()
        if self.state.IF["nop"]:
            self.halted = True
            self.nextState.IF["PC"] = self.state.IF["PC"]
            self.nextState.IF["nop"] = self.state.IF["nop"]
            self.myRF.outputRF(self.cycle)
            self.printState(self.nextState, self.cycle)
            self.state = self.nextState
            self.cycle += 1
            return
        PC = self.state.IF["PC"]
        instr = self.ext_imem.readInstr(PC)
        decoded = decode(instr)
        ex = execute(decoded, self.myRF)
        if ex["halt"]:
            self.inst_count += 1
            self.nextState.IF["PC"] = PC
            self.nextState.IF["nop"] = True
            self.myRF.outputRF(self.cycle)
            self.printState(self.nextState, self.cycle)
            self.state = self.nextState
            self.cycle += 1
            return
        if ex["rd_mem"]:
            mem_val = self.ext_dmem.readInstr(ex["mem_addr"]) & 0xFFFFFFFF
            ex["alu_result"] = mem_val
        if ex["wrt_mem"]:
            self.ext_dmem.writeDataMem(ex["mem_addr"], ex["store_data"])
        if ex["wrt_enable"]:
            self.myRF.writeRF(ex["rd"], ex["alu_result"])
        if ex["branch_taken"]:
            if decoded["opcode"] == "1101111":
                self.myRF.writeRF(ex["rd"], PC + 4)
                next_pc = PC + decoded["imm_j"]
            else:
                next_pc = PC + decoded["imm_b"]
        else:
            next_pc = PC + 4
        self.nextState.IF["PC"] = next_pc
        self.nextState.IF["nop"] = False
        self.inst_count += 1
        self.myRF.outputRF(self.cycle)
        self.printState(self.nextState, self.cycle)
        self.state = self.nextState
        self.cycle += 1

    def printState(self, state, cycle):
        printstate = ["-" * 70 + "\n", "State after executing cycle: " + str(cycle) + "\n", "IF.PC: " + str(state.IF["PC"]) + "\n", "IF.nop: " + str(state.IF["nop"]) + "\n"]
        perm = "w" if cycle == 0 else "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)

class FiveStageCore(Core):
    def __init__(self, ioDir, imem, dmem):
        super(FiveStageCore, self).__init__(ioDir + "\\FS_", imem, dmem)
        self.opFilePath = ioDir + "\\StateResult_FS.txt"
        self.inst_count = 0
        self.stall_count = 0
        self.halt_counted = False
        self.state.ID["nop"] = True
        self.state.EX["nop"] = True
        self.state.MEM["nop"] = True
        self.state.WB["nop"] = True

    def step(self):
        self.nextState = State()
        if not self.state.WB["nop"]:
            if self.state.WB["wrt_enable"]:
                self.myRF.writeRF(self.state.WB["Wrt_reg_addr"], self.state.WB["Wrt_data"])
            self.inst_count += 1
        else:
            self.nextState.WB["nop"] = True
        if not self.state.MEM["nop"]:
            wrt_data = self.state.MEM["ALUresult"]
            if self.state.MEM["rd_mem"]:
                wrt_data = self.ext_dmem.readInstr(self.state.MEM["ALUresult"]) & 0xFFFFFFFF
            if self.state.MEM["wrt_mem"]:
                self.ext_dmem.writeDataMem(self.state.MEM["ALUresult"], self.state.MEM["Store_data"])
            self.nextState.WB["nop"] = False
            self.nextState.WB["Wrt_data"] = wrt_data
            self.nextState.WB["Wrt_reg_addr"] = self.state.MEM["Wrt_reg_addr"]
            self.nextState.WB["wrt_enable"] = self.state.MEM["wrt_enable"]
            self.nextState.WB["Rs"]  = self.state.MEM["Rs"]
            self.nextState.WB["Rt"] = self.state.MEM["Rt"]
        else:
            self.nextState.WB["nop"] = True
        if not self.state.EX["nop"]:
            a = self.state.EX["Read_data1"]
            b = self.state.EX["Read_data2"]
            imm = self.state.EX["Imm"]
            op = self.state.EX["alu_op"]
            if self.state.EX["is_I_type"] or self.state.EX["rd_mem"] or self.state.EX["wrt_mem"]:
                b = imm
            if op == "ADD": alu_out = a + b
            elif op == "SUB": alu_out = a - b
            elif op == "XOR": alu_out = a ^ b
            elif op == "OR": alu_out = a | b
            elif op == "AND": alu_out = a & b
            elif op == "PASS_A": alu_out = a
            else: alu_out = a + b
            alu_out = alu_out & 0xFFFFFFFF
            self.nextState.MEM["nop"] = False
            self.nextState.MEM["ALUresult"] = alu_out
            self.nextState.MEM["Store_data"] = self.state.EX["Read_data2"]
            self.nextState.MEM["Wrt_reg_addr"] = self.state.EX["Wrt_reg_addr"]
            self.nextState.MEM["rd_mem"] = self.state.EX["rd_mem"]
            self.nextState.MEM["wrt_mem"] = self.state.EX["wrt_mem"]
            self.nextState.MEM["wrt_enable"] = self.state.EX["wrt_enable"]
            self.nextState.MEM["Rs"] = self.state.EX["Rs"]
            self.nextState.MEM["Rt"] = self.state.EX["Rt"]
        else:
            self.nextState.MEM["nop"] = True
        stall = False
        branch_taken = False
        branch_target = 0
        halt_detected = False
        if not self.state.ID["nop"]:
            instr = self.state.ID["Instr"]
            id_pc = self.state.ID.get("PC", 0)
            d = decode(instr)
            opcode = d["opcode"]
            rs1, rs2, rd = d["rs1"], d["rs2"], d["rd"]
            if opcode == "1111111":
                halt_detected = True
                self.nextState.EX["nop"] = True
                if not self.halt_counted:
                    self.inst_count += 1
                    self.halt_counted = True
            else:
                if (not self.state.EX["nop"] and self.state.EX["rd_mem"] and self.state.EX["Wrt_reg_addr"] != 0 and (self.state.EX["Wrt_reg_addr"] == rs1 or self.state.EX["Wrt_reg_addr"] == rs2)):
                    stall = True
                    self.stall_count += 1
                if not stall:
                    rs1_val = self.myRF.readRF(rs1)
                    rs2_val = self.myRF.readRF(rs2)
                    if (not self.state.MEM["nop"] and
                        self.state.MEM["wrt_enable"] and
                        self.state.MEM["Wrt_reg_addr"] != 0):
                        fwd = (self.nextState.WB["Wrt_data"]
                            if self.state.MEM["rd_mem"]
                            else self.state.MEM["ALUresult"])
                        if self.state.MEM["Wrt_reg_addr"] == rs1: rs1_val = fwd
                        if self.state.MEM["Wrt_reg_addr"] == rs2: rs2_val = fwd
                    if (not self.state.EX["nop"] and
                        self.state.EX["wrt_enable"] and
                        self.state.EX["Wrt_reg_addr"] != 0):
                        fwd = self.nextState.MEM["ALUresult"]
                        if self.state.EX["Wrt_reg_addr"] == rs1: rs1_val = fwd
                        if self.state.EX["Wrt_reg_addr"] == rs2: rs2_val = fwd
                    if opcode == "1100011":
                        if d["funct3"] == "000":
                            branch_taken = (rs1_val == rs2_val)
                        elif d["funct3"] == "001":
                            branch_taken = (rs1_val != rs2_val)
                        branch_target = id_pc + d["imm_b"]
                        self.nextState.EX["nop"] = True
                        self.inst_count += 1
                    elif opcode == "1101111":
                        branch_taken = True
                        branch_target = id_pc + d["imm_j"]
                        self.nextState.EX["nop"] = False
                        self.nextState.EX["Read_data1"] = id_pc + 4
                        self.nextState.EX["Read_data2"] = 0
                        self.nextState.EX["Imm"] = 0
                        self.nextState.EX["Rs"] = rs1
                        self.nextState.EX["Rt"] = rs2
                        self.nextState.EX["Wrt_reg_addr"] = rd
                        self.nextState.EX["is_I_type"] = False
                        self.nextState.EX["rd_mem"] = False
                        self.nextState.EX["wrt_mem"] = False
                        self.nextState.EX["alu_op"] = "PASS_A"
                        self.nextState.EX["wrt_enable"] = True
                    else:
                        funct3 = d["funct3"]
                        funct7 = d["funct7"]
                        if opcode == "0110011":
                            is_I = False; rd_mem = False; wrt_mem = False; wrt_en = True; imm = 0
                            if funct3 == "000": op = "ADD" if funct7 == "0000000" else "SUB"
                            elif funct3 == "100": op = "XOR"
                            elif funct3 == "110": op = "OR"
                            elif funct3 == "111": op = "AND"
                            else: op = "ADD"
                        elif opcode == "0010011":
                            is_I = True; rd_mem = False; wrt_mem = False; wrt_en = True; imm = d["imm_i"]
                            if funct3 == "000": op = "ADD"
                            elif funct3 == "100": op = "XOR"
                            elif funct3 == "110": op = "OR"
                            elif funct3 == "111": op = "AND"
                            else: op = "ADD"
                        elif opcode == "0000011":
                            is_I = True; rd_mem = True; wrt_mem = False; wrt_en = True
                            imm = d["imm_i"]; op = "ADD"
                        elif opcode == "0100011":
                            is_I = True; rd_mem = False; wrt_mem = True; wrt_en = False
                            imm = d["imm_s"]; op = "ADD"
                        else:
                            is_I = False; rd_mem = False; wrt_mem = False; wrt_en = False
                            imm = 0; op = "ADD"
                        self.nextState.EX["nop"]= False
                        self.nextState.EX["Read_data1"] = rs1_val
                        self.nextState.EX["Read_data2"] = rs2_val
                        self.nextState.EX["Imm"] = imm
                        self.nextState.EX["Rs"] = rs1
                        self.nextState.EX["Rt"] = rs2
                        self.nextState.EX["Wrt_reg_addr"] = rd
                        self.nextState.EX["is_I_type"] = is_I
                        self.nextState.EX["rd_mem"] = rd_mem
                        self.nextState.EX["wrt_mem"] = wrt_mem
                        self.nextState.EX["alu_op"] = op
                        self.nextState.EX["wrt_enable"] = wrt_en
                else: 
                    self.nextState.EX["nop"] = True
        else:
            self.nextState.EX["nop"] = True
        if halt_detected:
            self.nextState.IF["nop"] = True
            self.nextState.ID["nop"] = True
            self.nextState.EX["nop"] = True
        elif stall:
            self.nextState.IF["PC"] = self.state.IF["PC"]
            self.nextState.IF["nop"] = self.state.IF["nop"]
            self.nextState.ID["nop"] = False
            self.nextState.ID["Instr"] = self.state.ID["Instr"]
            self.nextState.ID["PC"] = self.state.ID.get("PC", 0)
        elif branch_taken: 
            self.nextState.IF["PC"] = branch_target
            self.nextState.IF["nop"] = False
            self.nextState.ID["nop"] = True
        else:
            if not self.state.IF["nop"]:
                PC = self.state.IF["PC"]
                self.nextState.ID["Instr"] = self.ext_imem.readInstr(PC)
                self.nextState.ID["nop"] = False
                self.nextState.ID["PC"] = PC
                self.nextState.IF["PC"] = PC + 4
                self.nextState.IF["nop"] = False
            else:
                self.nextState.ID["nop"] = True
                self.nextState.IF["nop"] = True
        if (self.state.IF["nop"] and self.state.ID["nop"] and self.state.EX["nop"] and self.state.MEM["nop"] and self.state.WB["nop"]):
            self.halted = True
        self.myRF.outputRF(self.cycle)
        self.printState(self.nextState, self.cycle)
        self.state = self.nextState
        self.cycle += 1

    def printState(self, state, cycle):
        printstate = ["-" * 70 + "\n", "State after executing cycle: " + str(cycle) + "\n"]
        printstate.append("IF.nop: " + str(state.IF["nop"]) + "\n")
        printstate.append("IF.PC: " + str(state.IF["PC"]) + "\n")
        printstate.append("ID.nop: " + str(state.ID["nop"]) + "\n")
        printstate.append("ID.Instr: " + str(state.ID["Instr"]) + "\n")
        printstate.append("ID.PC: " + str(state.ID["PC"]) + "\n")
        printstate.append("EX.nop: " + str(state.EX["nop"]) + "\n")
        printstate.append("EX.Read_data1: " + str(state.EX["Read_data1"]) + "\n")
        printstate.append("EX.Read_data2: " + str(state.EX["Read_data2"]) + "\n")
        printstate.append("EX.Imm: " + str(state.EX["Imm"]) + "\n")
        printstate.append("EX.Rs: " + str(state.EX["Rs"]) + "\n")
        printstate.append("EX.Rt: " + str(state.EX["Rt"]) + "\n")
        printstate.append("EX.Wrt_reg_addr: " + str(state.EX["Wrt_reg_addr"]) + "\n")
        printstate.append("EX.is_I_type: " + str(state.EX["is_I_type"]) + "\n")
        printstate.append("EX.rd_mem: " + str(state.EX["rd_mem"]) + "\n")
        printstate.append("EX.wrt_mem: " + str(state.EX["wrt_mem"]) + "\n")
        printstate.append("EX.alu_op: " + str(state.EX["alu_op"]) + "\n")
        printstate.append("EX.wrt_enable: " + str(state.EX["wrt_enable"]) + "\n")
        printstate.append("MEM.nop: " + str(state.MEM["nop"]) + "\n")
        printstate.append("MEM.ALUresult: " + str(state.MEM["ALUresult"]) + "\n")
        printstate.append("MEM.Store_data: " + str(state.MEM["Store_data"]) + "\n")
        printstate.append("MEM.Rs: " + str(state.MEM["Rs"]) + "\n")
        printstate.append("MEM.Rt: " + str(state.MEM["Rt"]) + "\n")
        printstate.append("MEM.Wrt_reg_addr: " + str(state.MEM["Wrt_reg_addr"]) + "\n")
        printstate.append("MEM.rd_mem: " + str(state.MEM["rd_mem"]) + "\n")
        printstate.append("MEM.wrt_mem: " + str(state.MEM["wrt_mem"]) + "\n")
        printstate.append("MEM.wrt_enable: " + str(state.MEM["wrt_enable"]) + "\n")
        printstate.append("WB.nop: " + str(state.WB["nop"]) + "\n")
        printstate.append("WB.Wrt_data: " + str(state.WB["Wrt_data"]) + "\n")
        printstate.append("WB.Rs: " + str(state.WB["Rs"]) + "\n")
        printstate.append("WB.Rt: " + str(state.WB["Rt"]) + "\n")
        printstate.append("WB.Wrt_reg_addr: " + str(state.WB["Wrt_reg_addr"]) + "\n")
        printstate.append("WB.wrt_enable: " + str(state.WB["wrt_enable"]) + "\n")
        perm = "w" if cycle == 0 else "a"
        with open(self.opFilePath, perm) as wf:
            wf.writelines(printstate)

def selectFiles():
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw() 
    messagebox.showinfo("Imem", "Select the imem file")
    imem_path = filedialog.askopenfilename(
        title="Select imem.txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if not imem_path:
        return None, None
    messagebox.showinfo("Dmem", "Select the dmem file")
    dmem_path = filedialog.askopenfilename(
        title="Select dmem.txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
    )
    if not dmem_path:
        return None, None
    root.destroy()
    imem_dir = os.path.dirname(imem_path)
    dmem_dir = os.path.dirname(dmem_path)
    if imem_dir != dmem_dir:
        tk.Tk().withdraw()
        messagebox.showerror("Error", "imem and dmem need to be in the same directory")
        return None, None
    return imem_path, dmem_dir

if __name__ == "__main__":
     
    #parse arguments for input file location
    parser = argparse.ArgumentParser(description='RV32I processor')
    parser.add_argument('--iodir', default="", type=str, help='Directory containing the input files.')
    args = parser.parse_args()

    if args.iodir:
        ioDir = os.path.abspath(args.iodir)
    else:
        imem_path, ioDir = selectFiles()
        if ioDir is None:
            exit(1)
    print("IO Directory:", ioDir)

    imem = InsMem("Imem", ioDir)
    dmem_ss = DataMem("SS", ioDir)
    dmem_fs = DataMem("FS", ioDir)
    
    ssCore = SingleStageCore(ioDir, imem, dmem_ss)
    fsCore = FiveStageCore(ioDir, imem, dmem_fs)

    while(True):
        if not ssCore.halted:
            ssCore.step()
        
        if not fsCore.halted:
            fsCore.step()

        if ssCore.halted and fsCore.halted:
            break
    
    # dump SS and FS data mem.
    dmem_ss.outputDataMem()
    dmem_fs.outputDataMem()
    ssCore.reportMetrics("Single Stage", ioDir, mode="w")
    fsCore.reportMetrics("Five Stage", ioDir, mode="a")