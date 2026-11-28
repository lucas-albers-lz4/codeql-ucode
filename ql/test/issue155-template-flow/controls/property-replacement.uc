import { stat } from 'fs';
const methods = { observe: { args: { service_name: 'service_name' }, call: function(request) {
  if (!request.args.service_name) return null;
  request.args.service_name = 'fixed';
        return stat(`${request.args.service_name}`);
} } };
return { 'luci.review.property-replacement': methods };
