接下来你需要实现歌单播放功能，具体目标：当用户传入一个歌单id/链接的时候（例如： https://music.163.com/playlist?id=17605775246&uct2=U2FsdGVkX18FgwN5tFyCK7IUwymWCT/sk3wcgOQXoN0=）你需要提取出他的id或者直接使用id，用这个接口查询（localhost:3002）
这是接口的说明文档：
获取歌单详情
说明 : 歌单能看到歌单名字, 但看不到具体歌单内容 , 调用此接口 , 传入歌单 id, 可 以获取对应歌单内的所有的音乐(未登录状态只能获取不完整的歌单,登录后是完整的)，但是返回的 trackIds 是完整的，tracks 则是不完整的，可拿全部 trackIds 请求一次 song/detail 接口获取所有歌曲的详情 (https://github.com/Binaryify/NeteaseCloudMusicApi/issues/452)

必选参数 : id : 歌单 id

可选参数 : s : 歌单最近的 s 个收藏者,默认为 8

接口地址 : /playlist/detail

调用例子 : /playlist/detail?id=24381616
这个可能会有用，根据需要选择
batch 批量请求接口
说明 : 登录后调用此接口 ,传入接口和对应原始参数(原始参数非文档里写的参数,需参考源码),可批量请求接口

接口地址 : /batch

调用例子 : 使用 GET 方式:/batch?/api/v2/banner/get={"clientType":"pc"} 使用 POST 方式传入参数:{ "/api/v2/banner/get": {"clientType":"pc"} }

我需要你做好测试之后再正式实现到生产代码中，接受到这个任务之后，你需要打开一个终端，我会为你ssh到一个服务器，这个服务器上运行着这个后端端口（3002），开始