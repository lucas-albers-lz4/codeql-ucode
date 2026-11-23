'use strict';
import { popen } from 'fs';
const methods = {
 direct: { call: function(request) { popen(`echo ${source()}`); } },
 fixed: { call: function(request) { source(); popen(`echo fixed`); } },
 unrelated: { call: function(request) { source(); const other = 'fixed'; popen(`echo ${other}`); } },
 copy: { call: function(request) { const a = source(); popen(`echo ${a}`); } },
 overwrite: { call: function(request) { let a = source(); a = 'fixed'; popen(`echo ${a}`); } },
 shadow: { call: function(request) { let a = source(); { let a = 'fixed'; popen(`echo ${a}`); } } },
 unknown: { call: function(request) { popen(`echo ${unknown(source())}`); } }
};
return methods;
