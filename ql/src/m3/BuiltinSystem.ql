/**
 * @name Builtin system calls
 * @description Inventory of global builtin system(). Template-string probes stay unmodeled branches.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m3/builtin-system
 * @tags testing
 */

import codeql.ucode.m3.Models

from BuiltinSystemCall c
select c,
  "builtin system() in " + c.getLocation().getFile().getBaseName() + " at line " +
    c.getLocation().getStartLine().toString()
