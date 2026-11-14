'use strict';
import { popen } from 'fs';
const methods = { probe: { call: function(request) {
	popen(`echo ${true ? shellquote(request.args.value) : request.args.value} done`);
} } };
return methods;
