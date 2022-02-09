import React from 'react'
import {
    Modal,
    ModalOverlay,
    ModalContent,
    ModalHeader,
    ModalFooter,
    ModalBody,
    ModalCloseButton,
    Button,
  } from '@chakra-ui/react'
function AnalysisModal({ isOpenAnalse, onOpenAnalyse, onCloseAnalyse, children }) {
    return (
        <Modal isOpenAnalse={isOpenAnalse} onCloseAnalyse={onCloseAnalyse} size={'full'}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Analysis View</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            {children}
          </ModalBody>

          <ModalFooter>
            <Button colorScheme='blue' mr={3} onClick={onCloseAnalyse}>
              Close
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    )
}

export default AnalysisModal
