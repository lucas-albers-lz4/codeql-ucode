/**
 * @name Supported shellquote template shape
 * @description Regression-only syntactic context check; does not establish trusted quoting semantics.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m4/shellquote-template-shape
 * @tags testing
 */
import codeql.ucode.m3.Models
from RequestArgsAccess src, NamedCall sink
where
  (sink instanceof NamedFsPopenCall or sink instanceof BuiltinSystemCall) and
  src.getProperty().getValue() != "args" and
  supportedShellquoteTemplateShape(src, sink)
select src, "supported template shape in " + src.getLocation().getFile().getBaseName()
