from PIL import Image
import cv2
import numpy as np
from PySide2.QtGui import QImage

# https://github.com/Mugichoko445/Fast-Digital-Image-Inpainting/blob/master/sources/FastDigitalImageInpainting.hpp
def convertPIL2CV(img:Image):
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
def convertCV2PIL(img)->Image:
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

def convertQImageToCV2(img):
    """Converts a QImage into CV2 format."""

    img = img.convertToFormat(QImage.Format_RGB32)

    width = img.width()
    height = img.height()

    ptr = img.bits()
    arr = np.array(ptr).reshape(height, width, 4)

    return arr

_a = 0.073235
_b = 0.176765
_K = np.array([[_a, _b, _a,
                _b,  0, _b,
                _a, _b, _a]])

def fastInpaint(src, mask=None, kernel=None, maxIter=100):
    if not kernel:
        kernel = _K

    # Make mask BGR
    mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)

    # Fill masked region with average color
    avgColor = cv2.sumElems(src) // (np.prod(src.shape[:2]))
    avgColorMat = np.ones((1,1,3))
    avgColorMat[0,0] = np.asarray([avgColor[0], avgColor[1], avgColor[2]])
    avgColorMat = cv2.resize(avgColorMat, (src.shape[1], src.shape[0]), 0.0, 0.0, cv2.INTER_NEAREST)
    print(mask)
    result = np.multiply(mask//255, src) + np.multiply((1 - mask//255), avgColorMat)

    # Convolution
    bSize = _K.shape[0] // 2
    # result.convertTo(result, CV_32FC3)
    result = (np.float32(result)-np.min(result))
    result /= np.max(result)

    # kernel3ch = cv2.cvtColor(kernel, cv2.COLOR_BGR2GRAY)
    kernel3ch = np.zeros((kernel.shape[0], kernel.shape[1], 3))
    for i in range(kernel.shape[0]):
        for j in range(kernel.shape[1]):
            kernel3ch[i,j,:] = 3*[kernel[i,j]]

    inWithBorder = cv2.copyMakeBorder(result, bSize, bSize, bSize, bSize, cv2.BORDER_REPLICATE)
    resInWithBorder = np.copy(inWithBorder[bSize:bSize+result.shape[0], bSize:bSize+result.shape[1]])

    # ch = result.shape[-1]
    for itr in range(maxIter):
        inWithBorder = cv2.copyMakeBorder(result, bSize, bSize, bSize, bSize, cv2.BORDER_REPLICATE)
        for r in range(result.shape[1]):
            for c in range(result.shape[0]):
                if np.all(mask[c,r,:] == 255):
                    roi = inWithBorder[c:c+_K.shape[1], r:r+_K.shape[0]]

                    s = cv2.sumElems(np.multiply(kernel3ch, roi))
                    result[c,r,0] = s[0]
                    result[c,r,1] = s[1]
                    result[c,r,2] = s[2]
                    
        # cv2.imshow("Inpainting...", result)
        # cv2.waitKey(1)


    result -= np.min(result)
    result *= 255/np.max(result)

    return np.uint8(result)



    # print(avgColor)
    # print(src.shape)