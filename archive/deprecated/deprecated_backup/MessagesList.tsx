{message.isSystemMessage || message.role === 'moderator' ? (
  <div className="bg-blue-50 p-3 rounded-lg border border-blue-200 mb-4">
    <h3 className="font-bold text-blue-700">진행자 메시지</h3>
    <p>{message.text}</p>
    <p className="text-xs text-gray-500 mt-1">
      {message.text.includes('초기메시지에용') ? '✅ 하드코딩된 메시지가 표시됨' : '❌ 하드코딩된 메시지 없음'}
    </p>
  </div>
) : (
  // 일반 메시지 렌더링
  <MessageBubble
    key={message.id}
    message={message}
    isUser={message.isUser}
    isContinuation={false} // 아바타를 항상 표시하도록 설정
    showTimestamp={true}
    showSender={true}
    senderName={senderName}
    senderType={senderType}
    npcDetails={npcDetails}
    replyToMessage={() => {}}
    citations={message.citations || []}
    side={side}
  />
)} 