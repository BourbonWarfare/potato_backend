from bw.server import WebHandler

def main():
    server = WebHandler()
    print(server.urls(), server.namespace())
    url_map = tuple([unpacked for url in server.urls() for unpacked in url])
    print(url_map)
    server.run()

if __name__ == '__main__':
    main()
