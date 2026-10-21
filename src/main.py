import winapi
from app import App


def main():
    # must happen before Tk creates any window
    winapi.enable_dpi_awareness()
    if not winapi.acquire_single_instance():
        return
    App().run()


if __name__ == "__main__":
    main()
