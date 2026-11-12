/**
 * @name shell-injection candidate
 * @description M4: request.args reaches popen/system without complete-argument shellquote. Quoted entire commands stay candidates (executable selection).
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/shell-injection-candidate
 * @tags testing
 */

import codeql.ucode.m3.Models

string exeNote(RequestArgsAccess src, NamedCall sink) {
  if quotedEntireCommand(src, sink)
  then result = " (quoted executable selection)"
  else result = ""
}

from RequestArgsAccess src, NamedCall sink
where
  (sink instanceof NamedFsPopenCall or sink instanceof BuiltinSystemCall) and
  src.getProperty().getValue() != "args" and
  shellInjectionCandidate(src, sink)
select src,
  "shell-injection candidate via " + sink.getName() + " in " +
    src.getLocation().getFile().getBaseName() + exeNote(src, sink), sink, sink.getName()
