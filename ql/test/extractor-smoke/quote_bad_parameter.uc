'use strict';
import { popen } from 'fs';
const methods = { probe: { call: function(request, shellquote) {
	popen(`echo ${shellquote(request.args.value)} done`);
} } };
return methods;
