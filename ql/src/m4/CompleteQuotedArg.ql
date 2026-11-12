/**
 * @name complete-argument shellquote
 * @description M4: request.args wrapped by shellquote as a template substitution into a larger popen/system command.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/complete-quoted-arg
 * @tags testing
 */

import codeql.ucode.m3.Models

from RequestArgsAccess src, NamedCall sink
where
  (sink instanceof NamedFsPopenCall or sink instanceof BuiltinSystemCall) and
  src.getProperty().getValue() != "args" and
  completeQuotedTemplateArg(src, sink)
select src,
  "complete-argument shellquote into " + sink.getName() + " in " +
    src.getLocation().getFile().getBaseName(), sink, sink.getName()
