# 多线程
```python
import threading
th = threading.Thread(target=matter2, args=(music, test))
th.start()
```
threading.Thread.join(th)为自闭方法，再th运行完后再运行后面的程序。

```python
import time
import threading


def matter1(music, test):
    print test, music
    # 假设每一首歌曲的时间是2秒
    time.sleep(2)


if __name__ == '__main__':
    # 设定我要听的歌为
    musics = ["music1", "music2", "music3"]
    test = "122678"
    # 开始时间
    start = time.time()

    threadpool = []

    for music in musics:
        th = threading.Thread(target=matter1, args=(music, test))
        threadpool.append(th)
    for th in threadpool:
        th.start()
    for th in threadpool:
        # 自闭
        threading.Thread.join(th)

    # 结束时间
    end = time.time()
    print("完成的时间为：" + str(end - start))
```