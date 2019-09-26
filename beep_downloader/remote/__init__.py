from abc import ABC, abstractmethod


class Remote(ABC):
    @abstractmethod
    def get_user_sites(self, include_beep, username, password):
        pass

    @abstractmethod
    def get_download_list(self, sites, cache, out_dir, forbidden_files):
        pass
