import { useState, useEffect, useCallback } from 'react';
import { DebateStage, DebateState, TurnInfo } from '../types/debate.types';

export function useDebateState() {
  const [debateState, setDebateState] = useState<DebateState>({
    currentStage: DebateStage.OPENING,
    isUserTurn: false,
    turnIndicatorVisible: false,
    selectedNpcId: null,
    isGeneratingResponse: false,
    isGeneratingNext: false,
    inputDisabled: true,
  });

  // 사용자 차례 설정
  const setUserTurn = useCallback((isUserTurn: boolean, showIndicator = true) => {
    setDebateState(prev => ({
      ...prev,
      isUserTurn,
      turnIndicatorVisible: isUserTurn && showIndicator,
      inputDisabled: !isUserTurn,
    }));
  }, []);

  // NPC 선택 상태 설정
  const setSelectedNpc = useCallback((npcId: string | null, autoHideDelay = 3000) => {
    setDebateState(prev => ({
      ...prev,
      selectedNpcId: npcId,
    }));

    // 자동으로 선택 해제
    if (npcId && autoHideDelay > 0) {
      setTimeout(() => {
        setDebateState(prev => ({
          ...prev,
          selectedNpcId: null,
        }));
      }, autoHideDelay);
    }
  }, []);

  // 응답 생성 상태 설정
  const setGeneratingResponse = useCallback((isGenerating: boolean) => {
    setDebateState(prev => ({
      ...prev,
      isGeneratingResponse: isGenerating,
    }));
  }, []);

  // Next 버튼 상태 설정
  const setGeneratingNext = useCallback((isGenerating: boolean) => {
    setDebateState(prev => ({
      ...prev,
      isGeneratingNext: isGenerating,
    }));
  }, []);

  // 토론 단계 변경
  const setCurrentStage = useCallback((stage: DebateStage) => {
    setDebateState(prev => ({
      ...prev,
      currentStage: stage,
    }));
  }, []);

  // 입력 필드 비활성화 여부 계산
  const isInputDisabled = useCallback((): boolean => {
    return !debateState.isUserTurn || debateState.isGeneratingResponse;
  }, [debateState.isUserTurn, debateState.isGeneratingResponse]);

  // 다음 메시지 버튼 표시 여부 계산
  const shouldShowNextMessageButton = useCallback((
    isDebateRoom: boolean,
    onRequestNextMessage?: () => void,
    messagesLength = 0
  ): boolean => {
    if (!isDebateRoom || !onRequestNextMessage || debateState.isGeneratingResponse) {
      return false;
    }
    // 토론방에서는 항상 Next 버튼 표시 (메시지 개수 무관)
    return true;
  }, [debateState.isGeneratingResponse]);

  // 차례 정보 업데이트 (소켓 이벤트에서 호출)
  const updateTurnInfo = useCallback((turnInfo: TurnInfo) => {
    setUserTurn(turnInfo.isUserTurn, true);
  }, [setUserTurn]);

  // 상태 초기화
  const resetDebateState = useCallback(() => {
    setDebateState({
      currentStage: DebateStage.OPENING,
      isUserTurn: false,
      turnIndicatorVisible: false,
      selectedNpcId: null,
      isGeneratingResponse: false,
      isGeneratingNext: false,
      inputDisabled: true,
    });
  }, []);

  return {
    // 상태
    debateState,
    isInputDisabled: isInputDisabled(),
    
    // 액션
    setUserTurn,
    setSelectedNpc,
    setGeneratingResponse,
    setGeneratingNext,
    setCurrentStage,
    updateTurnInfo,
    resetDebateState,
    
    // 계산된 값
    shouldShowNextMessageButton,
    
    // 개별 상태 값들 (편의성을 위해)
    currentStage: debateState.currentStage,
    isUserTurn: debateState.isUserTurn,
    turnIndicatorVisible: debateState.turnIndicatorVisible,
    selectedNpcId: debateState.selectedNpcId,
    isGeneratingResponse: debateState.isGeneratingResponse,
    isGeneratingNext: debateState.isGeneratingNext,
  };
} 