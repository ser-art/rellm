from typing import List, Union

import regex
from transformers import PreTrainedModel, PreTrainedTokenizer

from rellm.logits_mask import LogitsMask
from rellm.re_token_filter import ReTokenFilter


def complete_re(
    prompt: str,
    pattern: Union[regex.Pattern, List[regex.Pattern]],
    tokenizer: PreTrainedTokenizer,
    model: PreTrainedModel,
    max_new_tokens: int = 3,
    stop_after_match: bool = True,
    debug: bool = False,
    **model_kwargs
):
    """
    Complete a prompt with a regex pattern.
    """
    if isinstance(pattern, regex.Pattern):
        pattern = [pattern]

    gen_tokens = 0
    partial_completion = ""
    prompt_plus_completion = prompt + partial_completion

    token_filter = ReTokenFilter(tokenizer)

    while gen_tokens < max_new_tokens:
        prompt_token_ids = tokenizer.encode(prompt_plus_completion, return_tensors="pt")
        prompt_length = prompt_token_ids.shape[1]

        allowed_token_ids = token_filter.filter_tokens(partial_completion, pattern)
        custom_mask_processor = LogitsMask(allowed_token_ids)

        output_ids = model.generate(
            input_ids=prompt_token_ids,
            max_new_tokens=1,
            pad_token_id=tokenizer.eos_token_id,
            logits_processor=[custom_mask_processor],
            **model_kwargs
        )
        new_token_ids = output_ids[0, prompt_length:]
        output_text = tokenizer.decode(new_token_ids, skip_special_tokens=True)
        partial_completion += output_text
        prompt_plus_completion = prompt_plus_completion + output_text
        if debug:
            print("step={} completion={}".format(gen_tokens, partial_completion))

        if stop_after_match:
            for p in pattern:
                m = p.match(partial_completion)
                if m and m.start() == 0:
                    return m[0]
        gen_tokens += 1

    return partial_completion
