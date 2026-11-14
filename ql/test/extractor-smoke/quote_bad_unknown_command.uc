'use strict';
import { popen } from 'fs';
const methods = { probe: { call: function(request) {
	popen(`custom ${shellquote(request.args.value)} done`);
} } };
return methods;
