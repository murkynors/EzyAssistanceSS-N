import easyocr
import yaml

class OCRSingleton:
    instance = None
    def __init__(self):
        self._OCR = easyocr.Reader(self._load_languages())

    def _load_languages(self):
        try:
            with open('app_config.yaml', 'r', encoding='utf-8') as config_file:
                config_data = yaml.safe_load(config_file) or []
        except FileNotFoundError:
            return ['ch_sim', 'en']

        for item in config_data:
            if isinstance(item, dict) and 'ocrLanguages' in item:
                languages = item['ocrLanguages']
                if isinstance(languages, list) and languages:
                    return languages
        return ['ch_sim', 'en']

    @staticmethod
    def getInstance():
        if OCRSingleton.instance is None:
            OCRSingleton.instance = OCRSingleton()
        return OCRSingleton.instance

    def findTextPosition(self, img, text):

        # Perform OCR on the image
        result = self._OCR.readtext(img)
        for line in result:
            # print(line)
            if line[2] > 0.3:
                if text in line[1] or self._normalize_text(text) in self._normalize_text(line[1]):
                    positionRect = line[0]
                    center = ((positionRect[0][0] + positionRect[1][0]) / 2,
                              (positionRect[1][1] + positionRect[2][1]) / 2)
                    return (line[1], center)
        return None

    def _normalize_text(self, text):
        mapping = str.maketrans({
            '關': '关',
            '卡': '卡',
            '開': '开',
            '始': '始',
            '獎': '奖',
            '勵': '励',
            '領': '领',
        })
        return str(text).translate(mapping)

    def scanText(self, img):
        result = self._OCR.readtext(img)
        lineList = []
        for line in result:
            # print(line)
            if line[2] > 0.3:
                positionRect = line[0]
                center = ((positionRect[0][0] + positionRect[1][0]) / 2,
                          (positionRect[1][1] + positionRect[2][1]) / 2)
                lineList.append((line[1], center))
        return lineList

