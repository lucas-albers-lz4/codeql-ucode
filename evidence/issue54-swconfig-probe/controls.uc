'use strict';
import { popen } from 'fs';
const methods = {
 direct: { call: function(request) { popen(request.args.cmd); } },
 fixed: { call: function(request) { const unused = request.args.cmd; popen('fixed'); } },
 reassignment: { call: function(request) { let cmd = request.args.cmd; cmd = 'fixed'; popen(cmd); } },
 shadow: { call: function(request) { let cmd = request.args.cmd; { let cmd = 'fixed'; popen(cmd); } } },
 unknown: { call: function(request) { popen(`swconfig dev ${shellquote(request.args.cmd)} help`); } }
};
return methods;
