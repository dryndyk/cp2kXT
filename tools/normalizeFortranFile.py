#! /usr/bin/env python

import sys
import re
import string
from sys import argv
from cStringIO import StringIO

rUse=0
rVar=0
varRe=re.compile(r" *(?P<var>[a-zA-Z_0-9]+) *(?P<rest>(?:\((?P<param>(?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*)\))? *(?:= *(?P<value>(:?[^\"',()]+|\((?:[^()\"']+|\([^()\"']*\)|\"[^\"]*\"|'[^']*')*\)|\"[^\"]*\"|'[^']*')+))?)? *(?:(?P<continue>,)|\n?) *",re.IGNORECASE)
useParseRe=re.compile(
    r" *use +(?P<module>[a-zA-Z_][a-zA-Z_0-9]*)(?P<only> *, *only *:)? *(?P<imports>.*)$",
    flags=re.IGNORECASE)

def readFortranLine(infile):
    """Reads a group of connected lines (connected with &)
    returns a touple with the joined line, and a list with the original lines.
    Doesn't support multiline character constants!"""
    lineRe=re.compile(
        r"(?:(?P<preprocessor>#.*\n?)| *(&)?(?P<core>(?:[^&!\"']+|\"[^\"]*\"|'[^']*')*)(?P<continue>&)? *(?P<comment>!.*\n?)?\n?)",#$
        re.IGNORECASE)
    joinedLine=""
    comments=None
    lines=[]
    while 1:
        line=infile.readline()
        if not line: break
        m=lineRe.match(line)
        if not m or m.span()[1]!=len(line):
            raise SyntaxError("unexpected line format:"+repr(line))
        if m.group("preprocessor"):
            if len(lines)>0:
                raise SyntaxError("continuation to a preprocessor line not supported "+repr(line))
            lines.append(line)
            comments=line
            break
        joinedLine+=m.group("core")
        lines.append(line)
        if m.group("comment"):
            if comments:
                comments+=m.group("comment")
            else:
                comments=m.group("comment")
        if not m.group("continue"): break
    return (joinedLine,comments,lines)
    
def parseRoutine(inFile):
    """Parses a routine"""
    startRe=re.compile(r" *(?:recursive +|pure +|elemental +)*(?:subroutine|function)",re.IGNORECASE)
    endRe=re.compile(r" *end (?:subroutine|function)",re.IGNORECASE)
    startRoutineRe=re.compile(r" *(?:recursive +|pure +|elemental +)*(?P<kind>subroutine|function) +(?P<name>[a-zA-Z_][a-zA-Z_0-9]*) *(?:\((?P<arguments>[^()]*)\))? *(?:result *\( *(?P<result>[a-zA-Z_][a-zA-Z_0-9]*) *\))? *\n?",re.IGNORECASE)#$
    typeBeginRe=re.compile(r" *(?P<type>integer(?: *\* *[0-9]+)?|logical|character(?: *\* *[0-9]+)?|real(?: *\* *[0-9]+)?|complex(?: *\* *[0-9]+)?|type)",
                           re.IGNORECASE)
    typeRe=re.compile(r" *(?P<type>integer(?: *\* *[0-9]+)?|logical|character(?: *\* *[0-9]+)?|real(?: *\* *[0-9]+)?|complex(?: *\* *[0-9]+)?|type) *(?P<parameters>\((?:[^()]+|\([^()]*\))*\))? *(?P<attributes>(?: *, *[a-zA-Z_0-9]+(?: *\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\))?)+)? *(?P<dpnt>::)?(?P<vars>[^\n]+)\n?",re.IGNORECASE)#$
    attributeRe=re.compile(r" *, *(?P<attribute>[a-zA-Z_0-9]+) *(?:\( *(?P<param>(?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*)\))? *",re.IGNORECASE)
    ignoreRe=re.compile(r" *(?:|implicit +none *)$",re.IGNORECASE)
    interfaceStartRe=re.compile(r" *interface *$",re.IGNORECASE)
    interfaceEndRe=re.compile(r" *end +interface *$",re.IGNORECASE)
    routine={'preRoutine':[],
             'core':[],
             'strippedCore':[],
             'begin':[],
             'end':[],
             'preDeclComments':[],
             'declarations':[],
             'declComments':[],
             'parsedDeclarations':[],
             'postRoutine':[],
             'kind':None,'name':None,'arguments':None,'result':None,
             'interfaceCount':0,
             'use':[]
             }
    while 1:
        (jline,comments,lines)=readFortranLine(inFile)
        if len(lines)==0: break
        if startRe.match(jline):break
        routine['preRoutine'].extend(lines)
    if jline:
        routine['begin']=lines
        m=startRoutineRe.match(jline)
        if not m or m.span()[1]!=len(jline):
            raise SyntaxError("unexpected subroutine start format:"+repr(lines))
        routine['name']=m.group('name')
        routine['kind']=m.group('kind')
        if (m.group('arguments') and m.group('arguments').strip()):
            routine['arguments']=map(lambda x: x.strip(),
                                     m.group('arguments').split(","))
        if (m.group('result')):
            routine['result']=m.group('result')
        if (not routine['result'])and(routine['kind'].lower()=="function"):
            routine['result']=routine['name']
    while 1:
        (jline,comments,lines)=readFortranLine(inFile)
        if len(lines)==0: break
        if not ignoreRe.match(jline):
            if typeBeginRe.match(jline):
                m=typeRe.match(jline)
                if (m.group('type').lower()=='type' and
                    not m.group('parameters')):
                    break
                if not m or m.span()[1]!=len(jline):
                    raise SyntaxError("unexpected type format:"+repr(jline))
                decl={'type':m.group("type"),
                      'parameters':None,
                      'attributes':[],
                      'vars':[]}
                if m.group('parameters'):
                    decl['parameters']=(m.group("parameters").replace(" ","").
                                        replace(",",", "))
                str=m.group("attributes")
                while(str):
                    m2=attributeRe.match(str)
                    if not m2:
                        raise SyntaxError("unexpected attribute format "+
                                          repr(str)+" in "+repr(lines))
                    decl['attributes'].append(m2.group().replace(" ","").
                                              replace(",",", ")[2:])
                    str=str[m2.span()[1]:]
                str=m.group("vars")
                while 1:
                    m2=varRe.match(str)
                    if not m2:
                        raise SyntaxError("unexpected var format "+
                                          repr(str)+" in "+repr(lines))
                    var=m2.group("var")
                    if m2.group("param"):var+="("+m2.group("param")+")"
                    if m2.group("value"):
                        var+=" = "
                        var+=m2.group("value")
                    decl['vars'].append(var)
                    str=str[m2.span()[1]:]
                    if not m2.group("continue"):
                        if str:
                            raise SyntaxError("error parsing vars (leftover="+
                                              repr(str)+") in "+repr(lines))
                        break
                routine['parsedDeclarations'].append(decl)
            elif interfaceStartRe.match(jline):
                istart=lines
                interfaceDeclFile=StringIO()
                while 1:
                    (jline,comments,lines)=readFortranLine(inFile)
                    if interfaceEndRe.match(jline):
                        iend=lines
                        break
                    interfaceDeclFile.writelines(lines)
                interfaceDeclFile=StringIO(interfaceDeclFile.getvalue())
                iroutines=[]
                while 1:
                    iroutine=parseRoutine(interfaceDeclFile)
                    if not iroutine['kind']:
                        if len(iroutines)==0:
                            interfaceDeclFile.seek(0)
                            raise SyntaxError("error parsing interface:"+
                                              repr(interfaceDeclFile.read()))
                        iroutines[-1]['postRoutine'].extend(iroutine['preRoutine'])
                        break
                    iroutines.append(iroutine)
                for iroutine in iroutines:
                    routine['interfaceCount']+=1
                    decl={'type':'z_interface%02d'%(routine['interfaceCount']),
                          'parameters':None,
                          'attributes':[],
                          'vars':[iroutine['name']],
                          'iroutine':iroutine,
                          'istart':istart,
                          'iend':iend
                          }
                    routine['parsedDeclarations'].append(decl)
            elif useParseRe.match(jline):
                routine['use'].append("".join(lines))
            else:
                break
        routine['declarations'].append("".join(lines))
        if (len(routine['parsedDeclarations'])==0 and len(routine['use'])==0 and
            not re.match(" *implicit +none *$",jline,re.IGNORECASE)):
            routine['preDeclComments'].append("".join(lines))
        elif comments:
            routine['declComments'].append(comments)
    while len(lines)>0:
        if endRe.match(jline):
            routine['end']=lines
            break
        routine['strippedCore'].append(jline)
        routine['core'].append("".join(lines))
        (jline,comments,lines)=readFortranLine(inFile)
    return routine

def findWord(word,text):
    """Returns the position of word in text or -1 if not found.
    A match is valid only if it is a whole word (i.e. findWord('try','retry')
    returns false)"""
    pos=text.find(word)
    while((pos>0 and (text[pos-1].isalnum() or
                      text[pos-1]=='%' or (text[pos-1]=='_'and
                       (pos==1 or text[pos-2].isalpha())) )) or
          (pos>=0 and pos+len(word)<len(text) and
           (text[pos+len(word)].isalnum() or text[pos+len(word)]=='_'))):
        pos=text.find(word,pos+1)
    return pos

def enforceDeclDependecies(declarations):
    """enforces the dependencies between the vars
    and compacts the declarations, returns the variables needed by other variables"""
    idecl=0
    ii=0
    while idecl<len(declarations):
        typeParam="".join(declarations[idecl]['attributes'])
        if declarations[idecl]['parameters']:
            typeParam+=" "+declarations[idecl]['parameters']
        typeParam=typeParam.lower()
        
        ivar=0
        while ivar<len(declarations[idecl]['vars']):
            moved=0
            m=varRe.match(declarations[idecl]['vars'][ivar])
            if not m:
                raise SyntaxError('could not match var '+repr(declarations[idecl]['vars'][ivar]))
            rest=m.group("rest")
            rest=rest.lower()
            if rest:
                for ivar2 in range(ivar+1,len(declarations[idecl]['vars'])):
                    m=varRe.match(declarations[idecl]['vars'][ivar2])
                    if findWord(m.group('var').lower(),rest)!=-1:
                        moved=ivar2+1
            if moved:
                declarations[idecl]['vars'][moved:moved]=[
                    declarations[idecl]['vars'][ivar]]
                del declarations[idecl]['vars'][ivar]
            else:
                for idecl2 in range(idecl+1,len(declarations)):
                    for ivar2 in range(len(declarations[idecl2]['vars'])):
                        ii+=1
                        if ii>10000:
                            raise StandardError,"could not enforce all constraints"
                        m=varRe.match(declarations[idecl2]['vars'][ivar2])
                        if (ivar==0 and
                            findWord(m.group('var').lower(),typeParam)!=-1):
                            declarations.insert(idecl2+1,declarations[idecl])
                            del declarations[idecl]
                            ivar=0
                            moved=1
                            break
                        if rest and findWord(m.group('var').lower(),rest)!=-1:
                            if len(declarations[idecl]['vars'])>1:
                                newDecl={}
                                newDecl.update(declarations[idecl])
                                newDecl['vars']=[declarations[idecl]['vars'][ivar]]
                                declarations.insert(idecl2+1,newDecl)
                                del declarations[idecl]['vars'][ivar]
                            else:
                                declarations.insert(idecl2+1,
                                                    declarations[idecl])
                                del declarations[idecl]
                                ivar=0
                            moved=1
                            break
                    if moved:
                        break
            if not moved: ivar+=1
        idecl+=1

    for i in range(len(declarations)-1,0,-1):
        if (declarations[i]['normalizedType'].lower()==
            declarations[i-1]['normalizedType'].lower()):
            declarations[i-1]['vars'].extend(declarations[i]['vars'])
            del declarations[i]

def sortDeclarations(declarations):
    """sorts, compacts declarations and respects dependencies
    normalizedType has to be defined for the declarations"""

    declarations.sort(lambda x,y:cmp(x['normalizedType'].lower(),
                                  y['normalizedType'].lower()))
    
    for i in range(len(declarations)-1,0,-1):
        if (declarations[i]['normalizedType'].lower()==
            declarations[i-1]['normalizedType'].lower()):
            declarations[i-1]['vars'].extend(declarations[i]['vars'])
            del declarations[i]

    for decl in declarations:
        decl['vars'].sort(lambda x,y:cmp(x.lower(),y.lower()))
    enforceDeclDependecies(declarations)

def writeRoutine(routine, outFile):
    """writes the given routine to outFile"""
    outFile.writelines(routine["preRoutine"])
    outFile.writelines(routine["begin"])
    outFile.writelines(routine["declarations"])
    outFile.writelines(routine["core"])
    outFile.writelines(routine["end"])
    outFile.writelines(routine["postRoutine"])
    
def writeInCols(dLine,indentCol,maxCol,indentAtt,file):
    """writes out the strings (trying not to cut them) in dLine up to maxCol
    indenting each newline with indentCol.
    The '&' of the continuation line is at maxCol.
    indentAtt is the actual intent, and the new indent is returned"""
    strRe=re.compile(r"('[^'\n]*'|\"[^\"\n]*\")")
    nonWordRe=re.compile(r"(\W)")
    maxSize=maxCol-indentCol-1
    tol=min(maxSize/6,6)+indentCol
    for fragment in dLine:
        if indentAtt+len(fragment)<maxCol:
            file.write(fragment)
            indentAtt+=len(fragment)
        elif len(fragment.lstrip())<=maxSize:
            file.write("&\n"+(" "*indentCol))
            file.write(fragment.lstrip())
            indentAtt=indentCol+len(fragment.lstrip())
        else:
            sPieces=strRe.split(fragment)
            for sPiece in sPieces:
                if sPiece and (not (sPiece[0]=='"' or sPiece[0]=="'")):
                    subPieces=nonWordRe.split(sPiece)
                else:
                    subPieces=[sPiece]
                for subPiece in subPieces:
                    if indentAtt==indentCol:
                        file.write(subPiece.lstrip())
                        indentAtt+=len(subPiece.lstrip())
                    elif indentAtt<tol or indentAtt+len(subPiece)<maxCol:
                        file.write(subPiece)
                        indentAtt+=len(subPiece)
                    else:
                        file.write("&\n"+(" "*indentCol))
                        file.write(subPiece.lstrip())
                        indentAtt=indentCol+len(subPiece.lstrip())
    return indentAtt

def writeCompactDeclaration(declaration,file):
    """Writes a declaration in a compact way"""
    d=declaration
    if d.has_key('iroutine'):
        file.writelines(d['istart'])
        writeRoutine(d['iroutine'],file)
        file.writelines(d['iend'])
    else:            
        dLine=[]
        if len(d['vars'])>0:
            dLine.append("    "+d['type'])
            if d['parameters']: # do not drop empty parameter lists?
                dLine.append(d['parameters'])
            if d['attributes']:
                for a in d['attributes']:
                    dLine[-1:]=[dLine[-1]+", "]
                    dLine.append(a)
            dLine[-1:]=[dLine[-1]+" :: "]
            for var in d['vars'][:-1]:
                dLine.append(var+", ")
            dLine.append(d['vars'][-1])

        writeInCols(dLine,6,79,0,file)
        file.write("\n")

def writeExtendedDeclaration(declaration,file):
    """Writes a declaration in a nicer way (using more space)"""
    d=declaration
    if len(d['vars'])==0: return
    if d.has_key('iroutine'):
        file.writelines(d['istart'])
        writeRoutine(d['iroutine'],file)
        file.writelines(d['iend'])
    else:            
        dLine=[]
        dLine.append("    "+d['type'])
        if d['parameters']: # do not drop empty parameter lists?
            dLine.append(d['parameters'])
        if d['attributes']:
            for a in d['attributes']:
                dLine[-1:]=[dLine[-1]+", "]
                dLine.append(a)

        indentAtt=writeInCols(dLine,6,45,0,file)
        file.write(" "*(44-indentAtt))
        file.write(" :: ")
        indentAtt=48
        
        dLine=[]
        for var in d['vars'][:-1]:
            dLine.append(var+", ")
        dLine.append(d['vars'][-1])

        writeInCols(dLine,48,79,indentAtt,file)
        file.write("\n")

def writeDeclarations(parsedDeclarations,file):
    """Writes the declarations to the given file"""
    for d in parsedDeclarations:
        maxLenVar=0
        totalLen=0
        for v in d['vars']:
            maxLenVar=max(maxLenVar,len(v))
            totalLen+=len(v)
        if maxLenVar>30 or totalLen>75:
            writeCompactDeclaration(d,file)
        else:
            writeExtendedDeclaration(d,file)

def cleanDeclarations(routine):
    """cleans up the declaration part of the given parsed routine
    removes unused variables"""
    global rVar
    commentToRemoveRe=re.compile(r" *! *(?:interface|arguments|parameters|locals?|\** *local +variables *\**|\** *local +parameters *\**) *$",re.IGNORECASE)

    if not routine['kind']: return
    if (routine['core'] and
        re.match(" *type *[a-zA-Z_]+ *$",routine['core'][0],re.IGNORECASE)):
        print "*** routine %s contains local types, not fully cleaned ***"%(
            routine['name'])
    if re.search("^#","".join(routine['declarations']),re.MULTILINE):
        print "*** routine %s declarations contain preprocessor directives ***\n*** declarations not cleaned ***"%(
            routine['name'])
        return
    try:
        rest="".join(routine['strippedCore']).lower()
        paramDecl=[]
        decls=[]
        for d in routine['parsedDeclarations']:
            d['normalizedType']=d['type']
            if d['parameters']:
                d['normalizedType']+=d['parameters']
            if (d["attributes"]):
                d['attributes'].sort(lambda x,y:cmp(x.lower(),y.lower()))
                d['normalizedType']+=', '
                d['normalizedType']+=', '.join(d['attributes'])
            if "parameter" in map(str.lower,d['attributes']):
                paramDecl.append(d)
            else:
                decls.append(d)

        sortDeclarations(paramDecl)
        sortDeclarations(decls)

        if routine['arguments']:
            routine['lowercaseArguments']=map(lambda x:x.lower(),routine['arguments'])
        else:
            routine['lowercaseArguments']=[]
        if routine['result']: routine['lowercaseArguments'].append(routine['result'].lower())
        argDeclDict={}
        localDecl=[]
        for d in decls:
            localD={}
            localD.update(d)
            localD['vars']=[]
            argD=None
            for v in d['vars']:
                lowerV=varRe.match(v).group("var").lower()
                if lowerV in routine['lowercaseArguments']:
                    argD={}
                    argD.update(d)
                    argD['vars']=[v]
                    if argDeclDict.has_key(lowerV):
                        raise SyntaxError(
                            "multiple declarations not supported. var="+v+
                            " declaration="+str(d)+"routine="+routine['name'])
                    argDeclDict[lowerV]=argD
                else:
                    pos=findWord(lowerV,rest)
                    if (pos!=-1):
                        localD['vars'].append(v)
                    else:
                        print "removed var",lowerV,"in routine",routine['name']
                        rVar+=1
            if (len(localD['vars'])):
                localDecl.append(localD)
        argDecl=[]
        for arg in routine['lowercaseArguments']:
            argDecl.append(argDeclDict[arg])
        if routine['kind'].lower()=='function':
            aDecl=argDecl[:-1]
        else:
            aDecl=argDecl
        isOptional=0
        for arg in aDecl:
            attIsOptional= ("optional" in map(lambda x:x.lower(),
                                              arg['attributes']))
            if isOptional and not attIsOptional:
                print "*** warning non optional args %s after optional in routine %s" %(
                    repr(arg['vars']),routine['name'])
            if attIsOptional:
                isOptional=1
        enforceDeclDependecies(argDecl)

        newDecl=StringIO()
        for comment in routine['preDeclComments']:
            if not commentToRemoveRe.match(comment):
                newDecl.write(comment)
        newDecl.writelines(routine['use'])
        writeDeclarations(argDecl,newDecl)
        if argDecl and paramDecl:
            newDecl.write("\n")
        writeDeclarations(paramDecl,newDecl)
        if (argDecl or paramDecl) and localDecl:
            newDecl.write("\n")
        writeDeclarations(localDecl,newDecl)
        if argDecl or paramDecl or localDecl:
            newDecl.write("\n")
        wrote=0
        for comment in routine['declComments']:
            if not commentToRemoveRe.match(comment):
                newDecl.write(comment)
                wrote=1
        if wrote:
            newDecl.write("\n")
        routine['declarations']=[newDecl.getvalue()]
    except:
        if routine.has_key('name'):
            print "**** exception cleaning routine "+routine['name']+" ****"
        print "parsedDeclartions=",routine['parsedDeclarations']
        raise
    
def parseUse(inFile):
    """Parses the use statements in inFile
    The parsing stops at the first non use statement.
    Returns something like:
    ([{'module':'module1','only':['el1','el2=>el3']},...],
     '! comment1\\n!comment2...\\n',
     'last line (the line that stopped the parsing)')
    """
    lineNr=0
    preComments=[]
    modules=[]
    origLines=[]
    while 1:
        (jline,comments,lines)=readFortranLine(inFile)
        lineNr=lineNr+len(lines)
        if not lines: break
        origLines.append("".join(lines))
        # parse use
        m=useParseRe.match(jline)
        if m:
            useAtt={'module':m.group('module'),'comments':[]}
            
            if m.group('only'):
                useAtt['only']=map(string.strip,
                                   string.split(m.group('imports'),','))
            else:
                useAtt['renames']=map(string.strip,
                                      string.split(m.group('imports'),','))
		if useAtt['renames']==[""]: del useAtt['renames']
            if comments : useAtt['comments'].append(comments)
            # add use to modules
            modules.append(useAtt)
        elif jline and not jline.isspace():
            break
        else:
            if len(modules)==0:
                preComments.append(("".join(lines)))
            elif comments:
                modules[-1]['comments'].append(comments)
        
    return {'modules':modules,'preComments':preComments,
            'postLine':"".join(lines),'origLines':origLines[:-1]}

def normalizeModules(modules):
    """Sorts the modules and their export and removes duplicates.
    renames aren't sorted correctly"""
    # orders modules
    modules.sort(lambda x,y:cmp(x['module'],y['module']) )
    for i in range(len(modules)-1,0,-1):
        if modules[i]['module']==modules[i-1]['module']:
            if not (modules[i-1].has_key('only') and
                    modules[i].has_key('only')):
                raise SyntaxError('rejoining of module '+
                                  str(modules[i]['module'])+
                                  ' failed as at least one of the use is not a use ...,only:')
            modules[i-1]['only'].extend(modules[i]['only'])
            del modules[i]
    # orders imports
    for m in modules:
        if m.has_key('only'):
            m['only'].sort()
            for i in range(len(m['only'])-1,0,-1):
                if m['only'][i-1]==m['only'][i]: del m['only'][i]

def writeUseLong(modules,outFile):
    for m in modules:
        if m.has_key('only'):
            outFile.write("  USE "+m['module']+","+
                          string.rjust('ONLY: ',38-len(m['module'])))
            if m['only']: outFile.write(m['only'][0])
            for i in range(1,len(m['only'])):
                outFile.write(",&\n"+string.ljust("",45)+m['only'][i])
        else:
            outFile.write("  USE "+m['module'])
            if m.has_key('renames') and m['renames']:
                outFile.write(","+string.ljust("",38)+
                              m['renames'][0])
                for i in range(1,len(m['renames'])):
                    outFile.write(",&\n"+string.ljust("",45)+m['renames'][i])
        if m['comments']:
            outFile.write("\n")
            outFile.write('\n'.join(m['comments']))
        outFile.write("\n")

def cleanUse(modulesDict,rest):
    """Removes the unneded modules (the ones that are not used in rest)"""
    global rUse
    exceptions={"cp_a_l":1,"cp_to_string":1,"cp_error_type":1,"cp_assert":1,
                "cp_failure_level":1,"cp_warning_level":1,"cp_note_level":1,
                "cp_fatal_level":1,"cp_logger_type":1,"timeset":1,"timestop":1,
                "dp":1,"cp_error_get_logger":1, "cp_error_message":1}
    localNameRe=re.compile(" *(?P<localName>[a-zA-Z_0-9]+)(?: *= *> *[a-zA-Z_0-9]+)? *$")
    modules=modulesDict['modules']
    rest=rest.lower()
    for i in range(len(modules)-1,-1,-1):
        if modules[i].has_key("only"):
            els=modules[i]['only']
            for j in range(len(els)-1,-1,-1):
                m=localNameRe.match(els[j])
                if not m:
                    raise SyntaxError('could not parse use only:'+repr(els[j]))
                impAtt=m.group('localName').lower()
                if not exceptions.has_key(impAtt):
                    if findWord(impAtt,rest)==-1:
                        rUse+=1
                        print "removed USE",els[j]
                        del els[j]
            if len(modules[i]['only'])==0:
                if modules[i]['comments']:
                    modulesDict['preComments'].extend(modules[i]['comments'])
                del modules[i]

def rewriteFortranFile(inFile,outFile,logFile=sys.stdout):
    """rewrites the use statements and declarations of inFile to outFile.
    It sorts them and removes the repetitions."""
    import os.path
    moduleRe=re.compile(r" *module (?P<moduleName>[a-zA-Z_][a-zA-Z_0-9]*) *(?:!.*)?$",
                        flags=re.IGNORECASE)
    coreLines=[]
    while 1:
        line=inFile.readline()
        if not line: break
        if line[0]=='#':
            coreLines.append(line)
        outFile.write(line)
        m=moduleRe.match(line)
        if m:
            if (m.group('moduleName')!=os.path.basename(inFile.name)[0:-2]) :
                raise SyntaxError("Module name is different from filename ("+
                                  m.group('moduleName')+
                                  "!="+os.path.basename(inFile.name)[0:-2]+")")
            break
    try:
        modulesDict=parseUse(inFile)
        routines=[]
        coreLines.append(modulesDict['postLine'])
        routine=parseRoutine(inFile)
        coreLines.extend(routine['preRoutine'])
        routines.append(routine)
        while routine['kind']:
            routine=parseRoutine(inFile)
            routines.append(routine)
        map(cleanDeclarations,routines)
        for routine in routines:
            coreLines.extend(routine['declarations'])
            coreLines.extend(routine['strippedCore'])
        rest="".join(coreLines)
        if re.search('^#',"".join(modulesDict['origLines']),re.MULTILINE):
            print "*** use statements contains preprocessor directives, not cleaning ***"
            outFile.writelines(modulesDict['origLines'])
        else:
            cleanUse(modulesDict,rest)
            normalizeModules(modulesDict['modules'])
            outFile.writelines(modulesDict['preComments'])
            writeUseLong(modulesDict['modules'],outFile)
            if modulesDict['modules']:
                outFile.write('\n')
        outFile.write(modulesDict['postLine'])
        for routine in routines:
            writeRoutine(routine,outFile)
    except:
        import traceback
        logFile.write('-'*60+"\n")
        traceback.print_exc(file=logFile)
        logFile.write('-'*60+"\n")

        logFile.write("Processing file '"+inFile.name+"'\n")

if __name__ == '__main__':
    import os.path
    if len(sys.argv)<2:
        print "usage:", sys.argv[0]," out_dir file1 [file2 ...]"
    else:
        outDir=sys.argv[1]
        if not os.path.isdir(outDir):
            print "out_dir must be a directory"
            print "usage:", sys.argv[0]," out_dir file1 [file2 ...]"
        else:
            for fileName in sys.argv[2:]:
                print "normalizing",fileName
                infile=open(fileName,'r')
                outfile=open(os.path.join(outDir,
                                          os.path.basename(fileName)),'w')
                rewriteFortranFile(infile,outfile)
                infile.close()
                outfile.close()
            print "*** "*6
            print "removedUse=",rUse
            print "removedVar=",rVar
                # print "done"
