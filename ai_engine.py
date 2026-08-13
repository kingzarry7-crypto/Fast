    # =====================================================
    # GROQ
    # =====================================================
    def _groq(self, messages, image=None):
        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )
        
        prepared = []
        for message in messages:
            prepared.append({
                "role": message["role"],
                "content": message["content"]
            })
            
        # Add image handling (OpenAI-compatible format)
        if image:
            mime_type, image_bytes = image
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            data_url = f"data:{mime_type};base64,{encoded}"
            prepared.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze the attached image carefully and answer directly."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url}
                    }
                ]
            })

        payload = {
            "model": GROQ_MODEL,
            "messages": prepared,
            "temperature": 0.3,
            "max_tokens": 700
        }
        
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=120
        )
        
        if response.status_code != 200:
            try:
                error = response.json()
            except Exception:
                error = response.text
            raise RuntimeError(f"Groq API error: {error}")
            
        data = response.json()
        choices = data.get("choices", [])
        
        if not choices:
            raise RuntimeError("Groq returned no choices.")
            
        answer = choices[0].get("message", {}).get("content", "")
        
        if not answer:
            raise RuntimeError("Groq returned no text.")
            
        return self._clean_response(answer)
