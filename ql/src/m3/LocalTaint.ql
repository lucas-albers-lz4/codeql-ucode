/**
 * @name Local request.args taint to popen/system
 * @description Synthetic positive control: request.args reaching a named popen or builtin system argument.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m3/local-taint
 * @tags testing
 */

import codeql.ucode.m3.Models

from RequestArgsAccess src, NamedCall sink
where
  (sink instanceof NamedFsPopenCall or sink instanceof BuiltinSystemCall) and
  taintReachesSink(src, sink)
select src, "request.args reaches " + sink.getName() + " in " + src.getLocation().getFile().getBaseName(),
  sink, sink.getName()
