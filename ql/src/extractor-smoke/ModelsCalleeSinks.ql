/**
 * @name Models sink callee controls
 * @description Reports modeled popen and system call sites for positive and negative controls.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/models-callee-sinks
 * @tags testing
 */

import codeql.ucode.m3.Models

from NamedCall c
where c instanceof NamedFsPopenCall or c instanceof BuiltinSystemCall
select c, c.getName() + " at line " + c.getLocation().getStartLine().toString()
