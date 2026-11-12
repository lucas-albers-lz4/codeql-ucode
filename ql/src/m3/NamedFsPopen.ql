/**
 * @name Named fs popen calls
 * @description Inventory of popen imported from 'fs'.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m3/named-fs-popen
 * @tags testing
 */

import codeql.ucode.m3.Models

from NamedFsPopenCall c
select c, "named fs popen in " + c.getLocation().getFile().getBaseName()
