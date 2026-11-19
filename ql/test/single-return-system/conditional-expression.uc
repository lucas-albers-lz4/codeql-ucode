const methods = {
  setBlockDetect: { call: function(request) {
    return { result: request.allowed && system('/bin/true') == 0 };
  } }
};
return { luci: methods };
