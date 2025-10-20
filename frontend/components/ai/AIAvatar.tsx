'use client';
export default function AIAvatar({ name, active, onClick }:{name: string, active?: boolean, onClick?:()=>void}) {
  return (
    <button onClick={onClick} style={{
      border: active ? '3px solid #6b46c1' : '2px solid #aaa',
      borderRadius: 12,
      padding: 12,
      background: active ? '#f6f0ff' : '#fff',
      minWidth: 120
    }}>
      <div style={{fontWeight: 700}}>{name}</div>
      <div style={{fontSize: 12, opacity: 0.7}}>{active ? 'Selected' : 'Tap to select'}</div>
    </button>
  );
}
