import json

def main():
    user_input = input("Escribe una orden: ")
    steps = [
        {"step": 1, "action": "abrir navegador"},
        {"step": 2, "action": "buscar 'OpenAI ChatGPT'"}
    ]
    with open("parsed_steps/orden.json", "w", encoding="utf-8") as f:
        json.dump(steps, f, indent=2)
    print("Pasos guardados en parsed_steps/orden.json")

if __name__ == "__main__":
    main()
